import asyncio
import sys

from app.agent.tools.context import ToolContext
from app.agent.tools.registry import execute_tool


async def publish(event, data):
    print("EVENT", event, data)


async def main(owner: str, name: str) -> None:
    ctx = ToolContext(owner, name, publish)
    calls = [
        ("get_repo_tree", {}),
        ("read_file", {"path": "README.md"}),
        ("search_code", {"query": "app"}),
        ("list_issues", {"labels": "", "limit": 5}),
    ]
    for tool, args in calls:
        res = await execute_tool(ctx, tool, args)
        print(f"\n== {tool}: ok={res['ok']}\n   {res['summary']}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "pallets/flask"
    owner, name = target.split("/")
    asyncio.run(main(owner, name))