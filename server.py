from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Demo")


@mcp.tool()
def hello(name: str = "world") -> str:
    """Say hello"""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="stdio")
