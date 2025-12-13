from openai import OpenAI
from src.mcp_client import MCPClient
import os
import json

MODEL = "gpt-4o"
SYSTEM_PROMPT = """
    You are an AI assistant that help users based on the provided tools.
    You can call tools as needed to fulfill user requests.
    Carefully consider the available tools, their actions, and possible consequences of each action.
    You may call tools multiple times to complete the user's request.
    """
MAX_HISTORY_LENGTH = 50  # Limit message history to prevent token overflow
MAX_ITERATION = 10  # Limit max API calls per query


class OpenAIAgent:
    """Agent that uses OpenAI's GPT with MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.model = MODEL

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.openai = OpenAI(api_key=api_key)
        self.conversation_history = []
        self.system_prompt = SYSTEM_PROMPT

    async def process_query(self, query: str) -> str:
        """Process query using GPT + MCP tools"""

        self.conversation_history.append({"role": "user", "content": query})

        # Get MCP tools and convert to OpenAI format
        mcp_tools = await self.mcp_client.get_tools()
        tools = self._convert_tools_to_openai_format(mcp_tools)

        final_text = []

        for iteration in range(MAX_ITERATION):
            # Build messages with system prompt
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history

            response = self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
            )

            message = response.choices[0].message

            # Handle text response
            if message.content:
                final_text.append(message.content)
                self.conversation_history.append(
                    {"role": "assistant", "content": message.content}
                )

            # Handle tool calls
            if message.tool_calls:
                # Add assistant message with tool calls to history
                self.conversation_history.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    }
                )

                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    final_text.append(
                        f"[Calling tool '{tool_name}' with args {tool_args}]..."
                    )
                    result = await self.mcp_client.call_tool(tool_name, tool_args)

                    # Add tool result to history
                    self.conversation_history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result.content),
                        }
                    )

            # Check for stopping condition
            if response.choices[0].finish_reason == "stop":
                break

        return "\n".join(final_text)

    def _convert_tools_to_openai_format(self, mcp_tools: list) -> list:
        """Convert MCP tools to OpenAI function calling format"""
        openai_tools = []

        for tool in mcp_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "inputSchema", {"type": "object", "properties": {}}
                    ),
                },
            }
            openai_tools.append(openai_tool)

        return openai_tools

    async def chat_loop(self):
        """Interactive chat loop with the agent"""

        while True:
            try:
                user_input = input("Input: ")

                if user_input.lower() == "exit":
                    print("Exiting Agent chat loop")
                    break

                response = await self.process_query(user_input)
                print(f"Agent: {response}")

            except KeyboardInterrupt:
                print("\nExiting Agent chat loop")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
