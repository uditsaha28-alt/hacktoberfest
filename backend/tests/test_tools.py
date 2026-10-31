import asyncio

import pytest

from app.agent.tools import github_client
from app.agent.tools.context import ToolContext, is_ignored
from app.agent.tools.github_client import GitHubError
from app.agent.tools.read_file import MAX_CHARS
from app.agent.tools.registry import TOOL_SCHEMAS, execute_tool

TREE = [
    {"path": "README.md", "size": 1200},
    {"path": "src/app.py", "size": 800},
    {"path": "src/utils/helpers.py", "size": 300},
    {"path": "node_modules/x/index.js", "size": 10},
    {"path": "logo.png", "size": 5000},
]


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def ctx(monkeypatch):
    async def fake_get_repo(owner, name):
        return {"default_branch": "main", "description": "", "language": "Python", "stars": 1, "open_issues": 2}

    async def fake_get_tree(owner, name, branch):
        return TREE, False

    monkeypatch.setattr(github_client, "get_repo", fake_get_repo)
    monkeypatch.setattr(github_client, "get_tree", fake_get_tree)

    published = []

    async def publish(event, data):
        published.append((event, data))

    c = ToolContext("acme", "demo", publish)
    c.published = published
    return c


def test_is_ignored():
    assert is_ignored("node_modules/x/index.js")
    assert is_ignored("logo.png")
    assert is_ignored("package-lock.json")
    assert is_ignored("poetry.lock")
    assert not is_ignored("src/app.py")


def test_repo_tree_root(ctx):
    res = run(execute_tool(ctx, "get_repo_tree", {}))
    assert res["ok"]
    assert res["data"]["files"] == ["README.md"]
    assert res["data"]["directories"] == [{"name": "src", "files": 2}]


def test_repo_tree_subpath(ctx):
    res = run(execute_tool(ctx, "get_repo_tree", {"path": "src"}))
    assert res["data"]["files"] == ["app.py"]
    assert res["data"]["directories"] == [{"name": "utils", "files": 1}]


def test_repo_tree_missing_path(ctx):
    res = run(execute_tool(ctx, "get_repo_tree", {"path": "nope"}))
    assert res["ok"] is False


def test_read_file_truncates(ctx, monkeypatch):
    async def fake_get_file(owner, name, path):
        return {"text": "x" * 10000, "size": 10000}

    monkeypatch.setattr(github_client, "get_file", fake_get_file)
    res = run(execute_tool(ctx, "read_file", {"path": "README.md"}))
    assert res["ok"] and res["data"]["truncated"]
    assert len(res["data"]["content"]) == MAX_CHARS


def test_read_file_github_error_becomes_failed_observation(ctx, monkeypatch):
    async def boom(owner, name, path):
        raise GitHubError(404, "not_found", "File not found.")

    monkeypatch.setattr(github_client, "get_file", boom)
    res = run(execute_tool(ctx, "read_file", {"path": "missing.py"}))
    assert res["ok"] is False
    assert "not found" in res["summary"].lower()


def test_search_code_merges_path_and_content_hits(ctx, monkeypatch):
    async def fake_search(owner, name, query):
        return ["src/app.py", "src/other.py"]

    monkeypatch.setattr(github_client, "search_code", fake_search)
    res = run(execute_tool(ctx, "search_code", {"query": "app"}))
    assert res["data"]["paths"] == ["src/app.py", "src/other.py"]


def test_search_code_survives_github_failure(ctx, monkeypatch):
    async def boom(owner, name, query):
        raise GitHubError(429, "rate_limited", "limit")

    monkeypatch.setattr(github_client, "search_code", boom)
    res = run(execute_tool(ctx, "search_code", {"query": "app"}))
    assert res["ok"] and res["data"]["paths"] == ["src/app.py"]


def test_list_issues_skips_pull_requests(ctx, monkeypatch):
    async def fake_list_issues(owner, name, labels=None, per_page=30):
        return [
            {"number": 1, "title": "Bug", "html_url": "https://github.com/acme/demo/issues/1",
             "labels": [{"name": "good first issue"}], "body": None},
            {"number": 2, "title": "A PR", "html_url": "https://github.com/acme/demo/pull/2",
             "labels": [], "body": "", "pull_request": {}},
        ]

    monkeypatch.setattr(github_client, "list_issues", fake_list_issues)
    res = run(execute_tool(ctx, "list_issues", {"labels": "good first issue"}))
    assert [i["number"] for i in res["data"]["issues"]] == [1]
    assert 1 in ctx.issues_seen and 2 not in ctx.issues_seen


def test_write_section_publishes_and_strips_fences(ctx):
    md = "```mermaid\ngraph TD\n  A-->B\n```"
    res = run(execute_tool(ctx, "write_section", {"key": "diagram", "title": "Diagram", "markdown": md}))
    assert res["ok"]
    event, data = ctx.published[0]
    assert event == "section"
    assert data["markdown"] == "graph TD\n  A-->B"
    assert ctx.sections["diagram"]["title"] == "Diagram"


def test_write_section_rejects_unknown_key(ctx):
    res = run(execute_tool(ctx, "write_section", {"key": "bogus", "title": "x", "markdown": "y"}))
    assert res["ok"] is False
    assert ctx.published == []


def test_unknown_tool(ctx):
    assert run(execute_tool(ctx, "nope", {}))["ok"] is False


def test_bad_arguments_do_not_crash(ctx):
    assert run(execute_tool(ctx, "read_file", {"wrong": 1}))["ok"] is False


def test_schemas_cover_all_tools():
    names = {s["name"] for s in TOOL_SCHEMAS}
    assert names == {"get_repo_tree", "read_file", "search_code", "list_issues", "write_section"}