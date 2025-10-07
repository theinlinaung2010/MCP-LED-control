from src.mcp_client_anthropic import MCPClientAnthropic
from src.mcp_client_openai import MCPClientOpenAI
import asyncio
import sys


async def anthropic_client_loop(server_script_path: str):
    client = MCPClientAnthropic()
    try:
        await client.connect_to_server(server_script_path)
        await client.chat_loop()
    finally:
        await client.cleanup()


async def openai_client_loop(server_script_path: str):
    client = MCPClientOpenAI()
    try:
        await client.connect_to_server(server_script_path)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
    asyncio.run(anthropic_client_loop(sys.argv[1]))
    # asyncio.run(openai_client_loop(sys.argv[1]))
