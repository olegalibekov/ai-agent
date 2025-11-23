import json
from typing import Any, Dict, List, Tuple

from mcp import types as mcp_types
from mcp import ClientSession

from mcp_multi_client import MCPMultiClient


class ToolsRegistry:
    """
    Регистр всех MCP-тулов, конвертированных в формат tools для Responses API.
    Также хранит роутинг: имя тула → (session, mcp_tool_name).
    """

    def __init__(self, mcp_client: MCPMultiClient) -> None:
        self._mcp_client = mcp_client
        self.tools_for_llm: List[Dict[str, Any]] = []
        self._routes: Dict[str, Tuple[ClientSession, str]] = {}

    async def discover(self) -> None:
        """
        Сканируем все серверы, получаем tools/list и готовим инструменты для LLM.
        Используем стратегию 'serverName___toolName' для уникальности имён
        """
        async for server_name, session, tool in self._mcp_client.list_all_tools():
            assert isinstance(tool, mcp_types.Tool)

            llm_tool_name = f"{server_name}___{tool.name}"

            # MCP: tool.inputSchema — JSON Schema параметров
            input_schema = getattr(tool, "inputSchema", None) or {
                "type": "object",
                "properties": {},
            }

            self.tools_for_llm.append(
                {
                    "type": "function",
                    "name": llm_tool_name,
                    "description": tool.description or f"MCP tool {tool.name} from server {server_name}",
                    "parameters": input_schema,
                }
            )

            self._routes[llm_tool_name] = (session, tool.name)

    async def call_tool(self, llm_tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Вызвать MCP-tool по имени, которое видит модель (server___tool).
        Возвращаем строку (можно JSON-dump результата).
        """
        if llm_tool_name not in self._routes:
            raise ValueError(f"Unknown tool: {llm_tool_name}")

        session, mcp_tool_name = self._routes[llm_tool_name]
        result = await session.call_tool(mcp_tool_name, arguments)

        # result.content — список MCP ContentItem (обычно text / json).
        # Для простоты — собираем всё в строку.
        chunks: List[str] = []
        for item in result.content:
            item_type = getattr(item, "type", None)
            if item_type == "text":
                chunks.append(item.text)
            else:
                # На всякий случай сериализуем всё остальное
                chunks.append(json.dumps(item.model_dump(), ensure_ascii=False))
        if not chunks:
            return ""

        return "\n".join(chunks)
