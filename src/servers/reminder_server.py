from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("reminder-server", json_response=True)

_REMINDERS: list[dict] = []


@mcp.tool()
def create_reminder(task: str, when: str) -> dict:
    """
    Создать напоминание. В демо хранится в памяти процесса.
    """
    r = {
        "task": task,
        "when": when,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    _REMINDERS.append(r)
    return {"status": "ok", "reminder": r}


@mcp.tool()
def list_reminders() -> list[dict]:
    return _REMINDERS


if __name__ == "__main__":
    mcp.run()
