from src.mcp_client import MCPClient
from src.agent_anthropic import AnthropicAgent
from src.agent_openai import OpenAIAgent
import asyncio
import sys


async def run_anthropic_agent(server_script_path: str):
    client = MCPClient()
    try:
        await client.connect_to_server(server_script_path)
        agent = AnthropicAgent(client)

        # greet the user
        response = await agent.process_query("Greet user about yourself.")
        print(f"{response}")

        # start chat loop
        await agent.chat_loop()

    finally:
        await client.cleanup()


async def run_openai_agent(server_script_path: str):
    client = MCPClient()
    try:
        await client.connect_to_server(server_script_path)
        agent = OpenAIAgent(client)

        # greet the user
        response = await agent.process_query("Greet user about yourself.")
        print(f"{response}")

        # start chat loop
        await agent.chat_loop()

    finally:
        await client.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    asyncio.run(run_anthropic_agent(sys.argv[1]))
    # asyncio.run(run_openai_agent(sys.argv[1]))
