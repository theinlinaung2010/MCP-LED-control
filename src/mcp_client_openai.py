import asyncio
import os
import json
from typing import Optional, List, Dict, Any, Union
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI


class MCPClientOpenAI:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.openai = OpenAI(api_key=api_key)

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
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    def _convert_mcp_tools_to_openai_format(self, mcp_tools) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function calling format"""
        openai_tools = []

        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI ChatGPT and available tools"""
        if not self.session:
            return "Error: Not connected to MCP server"

        messages = [{"role": "user", "content": query}]

        # Get available tools from MCP server
        tools_response = await self.session.list_tools()
        mcp_tools = tools_response.tools

        # Convert MCP tools to OpenAI format
        openai_tools = self._convert_mcp_tools_to_openai_format(mcp_tools)

        # Create completion arguments
        completion_args = {
            "model": "gpt-4o",
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        # Add tools if available
        if openai_tools:
            completion_args["tools"] = openai_tools
            completion_args["tool_choice"] = "auto"

        # Initial OpenAI API call
        response = self.openai.chat.completions.create(**completion_args)

        final_text = []

        # Process the response
        message = response.choices[0].message

        if message.content:
            final_text.append(message.content)

        # Handle tool calls if any
        if message.tool_calls:
            # Add assistant's message to conversation
            assistant_message = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
            messages.append(assistant_message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Execute tool call via MCP
                try:
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_result_content = str(result.content)

                    # Add tool result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "content": tool_result_content,
                            "tool_call_id": tool_call.id,
                        }
                    )

                except Exception as e:
                    error_message = f"Error calling tool {tool_name}: {str(e)}"
                    final_text.append(error_message)

                    # Add error result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "content": error_message,
                            "tool_call_id": tool_call.id,
                        }
                    )

            # Create final completion arguments
            final_completion_args = {
                "model": "gpt-4o",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7,
            }

            if openai_tools:
                final_completion_args["tools"] = openai_tools
                final_completion_args["tool_choice"] = "auto"

            # Get final response from OpenAI after tool execution
            final_response = self.openai.chat.completions.create(
                **final_completion_args
            )

            final_message = final_response.choices[0].message
            if final_message.content:
                final_text.append(final_message.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client with OpenAI ChatGPT Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def client_main(server_script_path: str):
    """Main function to run the MCP client"""
    client = MCPClientOpenAI()
    try:
        await client.connect_to_server(server_script_path)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python mcp_client_openai.py <path_to_server_script>")
        print("Example: python mcp_client_openai.py mcp_server_weather.py")
        sys.exit(1)

    # Check if OPENAI_API_KEY is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required")
        print("Please set it using: set OPENAI_API_KEY=your_api_key_here")
        sys.exit(1)

    asyncio.run(client_main(sys.argv[1]))
