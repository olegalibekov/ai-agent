import json
from pathlib import Path
from typing import Dict, List, Any

from mcp.server.fastmcp import FastMCP

MESSAGES_FILE = Path("messages.json")

mcp = FastMCP("console-messages")


def _load_messages() -> Dict[str, Any]:
    if not MESSAGES_FILE.exists():
        return {"messages": []}
    with MESSAGES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


@mcp.tool()
def get_messages() -> Dict[str, List[Dict[str, str]]]:
    """
    MCP-инструмент:
    Возвращает все сообщения из messages.json.
    Формат:
    {
      "messages": [
        {"time": "HH:MM:SS", "text": "..."}, ...
      ]
    }
    """
    return _load_messages()


if __name__ == "__main__":
    # Старт MCP-сервера (через stdio – как обычно у FastMCP)
    mcp.run()
