import logging

from app.agent.tools.github_client import GitHubError
from app.agent.tools.list_issues import list_issues
from app.agent.tools.read_file import read_file
from app.agent.tools.repo_tree import get_repo_tree
from app.agent.tools.search_code import search_code
from app.agent.tools.write_section import ALLOWED_KEYS, write_section

logger = logging.getLogger(__name__)

TOOLS = {
    "get_repo_tree": get_repo_tree,
    "read_file": read_file,
    "search_code": search_code,
    "list_issues": list_issues,
    "write_section": write_section,
}

TOOL_SCHEMAS = [
    {
        "name": "get_repo_tree",
        "description": "List the files and folders directly inside one directory of the repo. Start with an empty path for the root, then go deeper.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Directory path, empty for the repo root."}},
            "required": [],
        },
    },
    {
        "name": "read_file",
        "description": "Read the text content of one file (long files are truncated).",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path, e.g. src/app.py"}},
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": "Find files by path or content keyword, e.g. a function name or 'router'.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Keyword to search for."}},
            "required": ["query"],
        },
    },
    {
        "name": "list_issues",
        "description": "List open GitHub issues. Use labels like 'good first issue' to find beginner tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "labels": {"type": "string", "description": "Comma-separated label filter, optional."},
                "limit": {"type": "integer", "description": "Max issues to return (1-30)."},
            },
            "required": [],
        },
    },
    {
        "name": "write_section",
        "description": "Publish one finished section of the onboarding report. For key 'diagram', markdown must be raw Mermaid source.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "enum": list(ALLOWED_KEYS)},
                "title": {"type": "string"},
                "markdown": {"type": "string"},
            },
            "required": ["key", "title", "markdown"],
        },
    },
]


async def execute_tool(ctx, name: str, args: dict | None) -> dict:
    fn = TOOLS.get(name)
    if fn is None:
        return {"ok": False, "summary": f"Unknown tool: {name}", "data": {}}
    try:
        return await fn(ctx, **(args or {}))
    except GitHubError as exc:
        return {"ok": False, "summary": exc.message, "data": {"error": exc.code}}
    except TypeError as exc:
        return {"ok": False, "summary": f"Invalid arguments for {name}.", "data": {"error": str(exc)}}
    except Exception:
        logger.exception("Tool %s crashed", name)
        return {"ok": False, "summary": f"{name} failed unexpectedly.", "data": {}}