# agent.py

import asyncio
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class TodoAgent:
    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._session: Optional[ClientSession] = None

    async def connect(self, server_script: str) -> None:
        """
        Запускает MCP-сервер (todo_mcp_server.py) и создаёт к нему MCP-сессию.
        """
        server_params = StdioServerParameters(
            command="python",
            args=[server_script],
            env=None,
        )

        stdio_transport = await self._stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport

        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

        tools_response = await self._session.list_tools()
        print("✅ Подключились к MCP-серверу.")
        print("   Доступные инструменты:")
        for t in tools_response.tools:
            print(f"   - {t.name}: {t.description}")

    async def get_todo_count_for_user(self, user_id: int) -> str:
        """
        Агент вызывает инструмент MCP и возвращает строку-результат.
        """
        if self._session is None:
            raise RuntimeError("Сначала вызови connect()")

        tool_name = "get_user_todo_count"
        args = {"user_id": user_id}

        print(f"\n👉 Вызываем MCP tool: {tool_name}({args})")
        result = await self._session.call_tool(tool_name, args)

        # result.content — это список блоков контента; для простоты вытащим текст первого
        if result.content and result.content[0].type == "text":
            return result.content[0].text

        return f"Неожиданный формат ответа: {result.content}"

    async def aclose(self) -> None:
        await self._stack.aclose()


async def main():
    agent = TodoAgent()

    # 1. Подключаемся к MCP-серверу
    await agent.connect("todo_mcp_server.py")

    # 2. Спрашиваем у пользователя ID и вызываем инструмент
    try:
        while True:
            raw = input("\nВведите user_id (1–10) или 'q' для выхода: ").strip()
            if raw.lower() in ("q", "quit", "exit"):
                break

            try:
                user_id = int(raw)
            except ValueError:
                print("Нужен целочисленный user_id")
                continue

            try:
                result = await agent.get_todo_count_for_user(user_id)
                print(f"\n🔎 Результат от MCP:\n{result}")
            except Exception as e:
                print(f"\n❌ Ошибка при вызове инструмента: {e}")
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
