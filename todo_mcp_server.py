# todo_mcp_server.py

from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("todo-server")

BASE_URL = "https://jsonplaceholder.typicode.com"


async def _fetch_todos_for_user(user_id: int) -> list[dict[str, Any]]:
    url = f"{BASE_URL}/todos"
    params = {"userId": user_id}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_user_todo_count(user_id: int) -> str:
    """
    Получить количество todo-задач для пользователя по его ID.

    Args:
      user_id: ID пользователя (целое число от 1 до 10)
    """
    todos = await _fetch_todos_for_user(user_id)
    done = sum(1 for t in todos if t.get("completed"))
    not_done = sum(1 for t in todos if not t.get("completed"))

    return (
        f"У пользователя {user_id} всего задач: {len(todos)}, "
        f"из них выполнено: {done}, не выполнено: {not_done}."
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
