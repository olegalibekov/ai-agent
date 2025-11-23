# /Users/fehty/PycharmProjects/ai-agent/src/main.py

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

from mcp_multi_client import MCPMultiClient, MCPServerConfig
from tools_registry import ToolsRegistry
from orchestrator import Orchestrator


async def main() -> None:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = AsyncOpenAI(api_key=api_key)

    # src/
    BASE_DIR = Path(__file__).resolve().parent
    SERVERS_DIR = BASE_DIR / "servers"

    print("Using servers dir:", SERVERS_DIR)

    mcp_client = MCPMultiClient()
    await mcp_client.start(
        [
            MCPServerConfig(
                name="search",
                command=[sys.executable, str(SERVERS_DIR / "search_server.py")],
            ),
            MCPServerConfig(
                name="summarize",
                command=[sys.executable, str(SERVERS_DIR / "summarize_server.py")],
            ),
        ]
    )

    tools_registry = ToolsRegistry(mcp_client)
    await tools_registry.discover()

    orchestrator = Orchestrator(client, tools_registry, model)

    print("MCP Orchestration demo. Ctrl+C to exit.\n")

    try:
        while True:
            user_text = input("You: ").strip()
            if not user_text:
                continue
            if user_text.lower() in {"quit", "exit"}:
                break

            answer = await orchestrator.run_dialog(user_text)
            print(f"\nAssistant:\n{answer}\n")
    finally:
        await mcp_client.stop()


if __name__ == "__main__":
    asyncio.run(main())
