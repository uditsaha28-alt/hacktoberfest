import asyncio
from typing import Any, Awaitable, Callable

from app.services.repo_url import parse_repo_url

Publish = Callable[[str, dict[str, Any]], Awaitable[None]]

STEP_DELAY = 0.7  # seconds between events; tests set this to 0


async def _pause() -> None:
    await asyncio.sleep(STEP_DELAY)


async def _tool(publish: Publish, call_id: str, tool: str, args: dict, summary: str) -> None:
    await publish("tool_call", {"id": call_id, "tool": tool, "args": args})
    await _pause()
    await publish("observation", {"id": call_id, "ok": True, "summary": summary})
    await _pause()


async def run_fake(repo_url: str, publish: Publish) -> dict:
    owner, name = parse_repo_url(repo_url)
    repo = f"{owner}/{name}"

    await publish(
        "plan",
        {"steps": ["Read repo tree", "Read README", "Locate entry points", "Check open issues", "Write report"]},
    )
    await _pause()

    await _tool(publish, "t1", "get_repo_tree", {"path": ""}, "Found 42 files across 6 directories")
    await _tool(publish, "t2", "read_file", {"path": "README.md"}, "Read README.md (2.1 KB)")

    await publish("plan", {"steps": ["Read src entry point", "Check open issues", "Write report"]})
    await _pause()

    summary_md = f"**{repo}** (scripted demo data, not a real analysis)."
    await publish("section", {"key": "summary", "title": "Overview", "markdown": summary_md})
    await _pause()

    await _tool(publish, "t3", "list_issues", {"limit": 10}, "Found 2 open issues")

    architecture_md = "The project has a UI layer, an API layer and a database."
    mermaid = "graph TD\n  UI[Frontend] --> API[Backend API]\n  API --> DB[(Database)]"
    setup_md = "1. Clone the repo\n2. Install dependencies\n3. Run the dev server"
    issues = [
        {
            "number": 1,
            "title": "Fix typo in README",
            "url": f"https://github.com/{repo}/issues/1",
            "reason": "Docs-only change, touches README.md",
            "difficulty": "easy",
        },
        {
            "number": 2,
            "title": "Add input validation",
            "url": f"https://github.com/{repo}/issues/2",
            "reason": "Small change in the API layer",
            "difficulty": "medium",
        },
    ]
    issues_md = "\n".join(f"- #{i['number']} {i['title']} ({i['difficulty']})" for i in issues)

    sections = [
        {"key": "architecture", "title": "Architecture", "markdown": architecture_md},
        {"key": "diagram", "title": "Diagram", "markdown": mermaid},
        {"key": "setup", "title": "Local setup", "markdown": setup_md},
        {"key": "first_issues", "title": "First contributions", "markdown": issues_md},
    ]
    for section in sections:
        await publish("section", section)
        await _pause()

    return {
        "repo": repo,
        "summary": summary_md,
        "sections": [{"key": "summary", "title": "Overview", "markdown": summary_md}, *sections],
        "mermaid": mermaid,
        "first_issues": issues,
    }