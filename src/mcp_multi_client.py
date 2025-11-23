# src/mcp_multi_client.py

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters


@dataclass
class MCPServerConfig:
    """
    Описание MCP-сервера.
    Пример:
        MCPServerConfig(
            name="search",
            command=["python", "servers/search_server.py"]
        )
    """
    name: str
    command: List[str]
    env: Optional[Dict[str, str]] = None


class MCPMultiClient:
    """
    Менеджер для подключения нескольких MCP-серверов одновременно.
    """

    def __init__(self) -> None:
        self._exit_stack = AsyncExitStack()
        self._sessions: Dict[str, ClientSession] = {}
        self._transports: Dict[str, Tuple[Any, Any]] = {}

    async def start(self, configs: List[MCPServerConfig]) -> None:
        """
        Подключиться ко всем MCP-серверам через stdio.
        """
        for cfg in configs:
            cmd = cfg.command[0]
            args = cfg.command[1:]

            params = StdioServerParameters(
                command=cmd,
                args=args,
                env=cfg.env,
            )

            # создаём stdio-транспорт
            read, write = await self._exit_stack.enter_async_context(stdio_client(params))

            # создаём MCP-сессию
            session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()

            # сохраняем
            self._sessions[cfg.name] = session
            self._transports[cfg.name] = (read, write)

    async def stop(self) -> None:
        """
        Закрыть все MCP-сессии.
        """
        await self._exit_stack.aclose()

    async def list_all_tools(self):
        """
        Асинхронный генератор: вернёт (server_name, session, tool_info)
        для каждого MCP-сервера и каждого инструмента в нём.
        """
        for server_name, session in self._sessions.items():
            response = await session.list_tools()

            for tool in response.tools:
                yield server_name, session, tool

    def get_session(self, server_name: str) -> ClientSession:
        return self._sessions[server_name]
