import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    # Параметры запуска сервера
    server_params = StdioServerParameters(
        command="python",  # чем запускать
        args=["server.py"],  # какой скрипт MCP-сервера
        env=None,
    )

    # stdio-клиент поднимает subprocess с сервером
    async with stdio_client(server_params) as (read, write):
        # создаём сессию
        async with ClientSession(read, write) as session:
            # handshake / initialize
            await session.initialize()

            # список инструментов
            tools_response = await session.list_tools()

            print("=== AVAILABLE TOOLS ===")
            for tool in tools_response.tools:
                print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
