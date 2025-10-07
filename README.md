# MCP OpenAI Test

Playground repo for learning and testing MCP (Model Context Protocol) server development with both Anthropic Claude and OpenAI ChatGPT.

https://modelcontextprotocol.io/

## Features

- **MCP LED control server**: MCP server for controlling an LED through Arduino compatible boards (tested on ESP6266).
- **Anthropic Client**: MCP client using Claude
- **OpenAI Client**: MCP client using ChatGPT

## Setup

1. **Install dependencies**:

   ```bash
   uv sync
   ```

2. **Set environment variables for API keys**

   ```powershell
   $env:OPENAI_API_KEY="your_openai_api_key"
   $env:ANTHROPIC_API_KEY="your_anthropic_api_key"
   ```

3. **Activate the virtual environment**:
   ```bash
   .venv\Scripts\Activate.ps1
   ```

## Usage

### Running the OpenAI MCP Client

```bash
python src/mcp_client_openai.py src/mcp_server_serial_led_control.py
```

### Running the Anthropic MCP Client

```bash
python src/mcp_client_anthropic.py src/mcp_server_serial_led_control.py
```

### Example Queries

Once the client is running, try these example queries:

- `"Turn on the LED"`
- `"Turn off the LED"`
- `"Toggle the LED"`
