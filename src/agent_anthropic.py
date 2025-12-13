from anthropic import Anthropic
from src.mcp_client import MCPClient
import os

MODEL = "claude-3-5-haiku-20241022"
SYSTEM_PROMPT = """
    You are an AI assistant that help users based on the provided tools.
    You can call tools as needed to fulfill user requests.
    Carefully consider the available tools, their actions, and possible consequences of each action.
    You may call tools multiple times to complete the user's request.
    """
MAX_HISTORY_LENGTH = 50  # Limit message history to prevent token overflow
MAX_ITERATION = 10  # Limit max API calls per query


class AnthropicAgent:
    """Agent that uses Anthropic's Claude with MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.model = MODEL
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.conversation_history = []
        self.system_prompt = SYSTEM_PROMPT

    async def process_query(self, query: str) -> str:
        """Process query using Claude + MCP tools"""

        self.conversation_history.append({"role": "user", "content": query})

        tools = await self.mcp_client.get_tools()
        final_text = []

        for iteration in range(MAX_ITERATION):
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=self.conversation_history,
                system=self.system_prompt,
                tools=tools,
            )

            for content in response.content:
                if content.type == "text":
                    final_text.append(content.text)
                    self.conversation_history.append(
                        {"role": "assistant", "content": [content]}
                    )

                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input

                    final_text.append(
                        f"[Calling tool '{tool_name}' with args {tool_args}]..."
                    )
                    result = await self.mcp_client.call_tool(tool_name, tool_args)

                    # Record tool use and result in conversation history
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

            # Check for stopping condition
            if response.stop_reason == "end_turn":
                break

        return "\n".join(final_text)

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
