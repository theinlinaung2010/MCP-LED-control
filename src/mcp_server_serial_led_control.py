# tutorial from https://modelcontextprotocol.io/docs/develop/build-server

from typing import Any
from mcp.server.fastmcp import FastMCP
import serial

# Initialize FastMCP server
mcp = FastMCP("serial_led_control")

# Constants
SERIAL_PORT = "COM5"
BAUD_RATE = 115200

CMD_LED_ON = "on"
CMD_LED_OFF = "off"
CMD_LED_STATUS = "status"


async def send_serial_command(command) -> str:
    # open serial port
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
        ser.write((command + "\n").encode())
        response = ser.readline().decode().strip()
        return response


@mcp.tool()
async def get_led_status() -> str:
    """Get the current status of the LED.

    Returns:
        A string indicating whether the LED is ON or OFF.
    """
    # get led status from the serial device
    led_status = await send_serial_command(CMD_LED_STATUS)
    return led_status


@mcp.tool()
async def control_led(action: str) -> str:
    """Control the LED on the ESP8266 device.

    Args:
        action: A string indicating the action to perform.
                Valid actions are "on", "off", and "status".

    Returns:
        A string indicating the result of the action.
    """
    if action not in [CMD_LED_ON, CMD_LED_OFF, CMD_LED_STATUS]:
        return f"Invalid action: {action}. Valid actions are 'on', 'off', and 'status'."

    # send command to the serial device
    result = await send_serial_command(action)
    return result


def debug_manual_input():
    # debug by user input
    while True:
        cmd = input("Enter command (on, off, status, exit): ").strip().lower()
        if cmd == "exit":
            print("Exiting...")
            break
        elif cmd in [
            CMD_LED_ON,
            CMD_LED_OFF,
            CMD_LED_STATUS,
        ]:
            import asyncio

            response = asyncio.run(send_serial_command(cmd))
            print(f"Response: {response}")
        else:
            print("Invalid command. Please try again.")


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
    # debug_manual_input()
