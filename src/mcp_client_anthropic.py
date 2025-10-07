import asyncio

from typing import Optional
from contextlib import AsyncExitStack
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic

# "claude-3-5-haiku-20241022"
# "claude-opus-4-1-20250805"
MODEL = "claude-3-5-haiku-20241022"
SYSTEM_PROMPT = """
    You are an AI assistant that help users based on the provided tools.
    You can call tools as needed to fulfill user requests.
    Carefully consider the available tools, their actions, and possible consequences of each action.
    You may call tools multiple times to complete the user's request.
    """
MAX_HISTORY_LENGTH = 50  # Limit message history to prevent token overflow
MAX_ITERATION = 10  # Limit max API calls per query


class MCPClientAnthropic:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.anthropic = Anthropic(api_key=api_key)

        # system prompt to guide Claude's behavior
        self.system_prompt = SYSTEM_PROMPT
        self.conversation_history = []
        self.max_history_length = MAX_HISTORY_LENGTH

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        tools_list = await self.session.list_tools()
        tools = tools_list.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        message = {"role": "user", "content": query}

        self.conversation_history.append(message)

        tools_list = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools_list.tools
        ]

        api_call_count = 0

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-opus-4-1-20250805",
            max_tokens=1000,
            # need to send full history for context since message API is stateless
            messages=self.conversation_history,
            system=self.system_prompt,
            tools=available_tools,
        )
        api_call_count += 1

        # Process response and handle tool calls
        final_text = []

        while api_call_count < MAX_ITERATION:
            for content in response.content:
                if content.type == "text":
                    final_text.append(content.text)
                    self.conversation_history.append(
                        {"role": "assistant", "content": [content]}
                    )

                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input

                    # Execute tool call
                    result = await self.session.call_tool(tool_name, tool_args)

                    final_text.append(
                        f"[Calling tool {tool_name} with args {tool_args}]"
                    )

                    # self.conversation_history.append(
                    #     {"role": "assistant", "content": [content]}
                    # )
                    self.conversation_history.append(
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": content.id,
                                    "name": tool_name,
                                    "input": tool_args,
                                }
                            ],
                        }
                    )
                    self.conversation_history.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content.id,
                                    "content": result.content,
                                }
                            ],
                        }
                    )

            # Get next response from Claude
            response = self.anthropic.messages.create(
                model="claude-opus-4-1-20250805",
                max_tokens=1000,
                messages=self.conversation_history,
                system=self.system_prompt,
                tools=available_tools,
            )
            api_call_count += 1

            # Check for end of response
            if response.stop_reason == "end_turn":
                return "\n".join(final_text)

        final_text.append(
            f"[Max iterations reached ({MAX_ITERATION}). Ending response.]"
        )

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

                # trim conversation history if too long
                if len(self.conversation_history) > self.max_history_length:
                    self.conversation_history.pop(0)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def client_main(server_script_path: str):
    client = MCPClientAnthropic()
    try:
        await client.connect_to_server(server_script_path)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    asyncio.run(client_main(sys.argv[1]))
