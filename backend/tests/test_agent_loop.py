import json
import asyncio

import pytest

from app.agent.llm.base import LLMError, LLMResponse, ToolCall
from app.agent.loop import run_agent
from app.agent.tools import github_client
from app.config import settings
from app.schemas import Report

URL = "https://github.com/acme/demo"
TREE = [
    {"path": "README.md", "size": 100},
    {"path": "src/app.py", "size": 200},
    {"path": "src/utils.py", "size": 50},
]
ISSUES = [
    {"number": 7, "title": "Add tests", "html_url": "https://github.com/acme/demo/issues/7",
     "labels": [{"name": "good first issue"}], "body": "x"},
    {"number": 9, "title": "Fix typo", "html_url": "https://github.com/acme/demo/issues/9",
     "labels": [], "body": ""},
]


def run(coro):
    return asyncio.run(coro)


class ScriptedLLM:
    name = "scripted"

    def __init__(self, steps):
        self.steps = list(steps)

    async def generate(self, system, history, tools):
        if not self.steps:
            raise LLMError("script exhausted")
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def call(name, **args):
    return ToolCall(name=name, args=args)


def reply(*calls, text=""):
    return LLMResponse(text=text, tool_calls=list(calls))


def idle(n=3):
    return [reply(text="Done.") for _ in range(n)]


def section(key, markdown="Some text."):
    return call("write_section", key=key, title=key.title(), markdown=markdown)


@pytest.fixture(autouse=True)
def fake_github(monkeypatch):
    async def get_repo(owner, name):
        return {"default_branch": "main", "description": "A demo app", "language": "Python",
                "stars": 1, "open_issues": 2}

    async def get_tree(owner, name, branch):
        return TREE, False

    async def list_issues(owner, name, labels=None, per_page=30):
        return ISSUES

    monkeypatch.setattr(github_client, "get_repo", get_repo)
    monkeypatch.setattr(github_client, "get_tree", get_tree)
    monkeypatch.setattr(github_client, "list_issues", list_issues)


def execute(steps):
    events = []

    async def publish(event, data):
        events.append((event, data))

    report = run(run_agent(URL, publish, llm=ScriptedLLM(steps)))
    return report, events


def observations(events):
    return [data for event, data in events if event == "observation"]


def test_happy_path_produces_valid_report_and_events():
    steps = [
        reply(call("update_plan", steps=["Read tree", "Check issues", "Write report"])),
        reply(call("get_repo_tree", path="")),
        reply(call("list_issues", labels="", limit=5)),
        reply(
            section("summary", "A demo app."),
            section("architecture"),
            section("diagram", "```mermaid\ngraph TD\n  A-->B\n```"),
            section("setup"),
            section("first_issues"),
        ),
        reply(call("submit_first_issues", issues=[{"number": 7, "reason": "Touches src/app.py", "difficulty": "easy"}])),
        reply(text="Done."),
    ]
    report, events = execute(steps)

    Report.model_validate(report)
    assert report["repo"] == "acme/demo"
    assert report["mermaid"] == "graph TD\n  A-->B"
    assert [i["number"] for i in report["first_issues"]] == [7]
    assert report["first_issues"][0]["title"] == "Add tests"
    assert [s["key"] for s in report["sections"]] == ["summary", "architecture", "diagram", "setup", "first_issues"]

    types = [event for event, _ in events]
    assert types[0] == "plan"
    assert types.count("plan") >= 2  # default plan plus the model's own
    assert types.count("tool_call") == types.count("observation")
    assert "done" not in types and "error" not in types  # run_manager owns those

    tools = [data["tool"] for event, data in events if event == "tool_call"]
    assert "update_plan" not in tools
    assert tools.count("write_section") == 5
    write_args = [d["args"] for e, d in events if e == "tool_call" and d["tool"] == "write_section"]
    assert all(set(a) <= {"key", "title"} for a in write_args)


def test_missing_sections_get_fallbacks_and_are_published():
    steps = [
        reply(call("list_issues", labels="", limit=5)),
        reply(section("summary")),
        *idle(),
    ]
    report, events = execute(steps)

    Report.model_validate(report)
    assert [s["key"] for s in report["sections"]] == ["summary", "architecture", "diagram", "setup", "first_issues"]
    assert report["mermaid"].startswith("graph TD")
    assert [i["number"] for i in report["first_issues"]] == [7, 9]
    published = [data["key"] for event, data in events if event == "section"]
    assert "diagram" in published and "first_issues" in published


def test_invented_issue_numbers_are_rejected():
    steps = [
        reply(call("list_issues", labels="", limit=5)),
        reply(section("summary")),
        reply(call("submit_first_issues", issues=[{"number": 999, "reason": "x", "difficulty": "easy"}])),
        *idle(),
    ]
    report, events = execute(steps)

    assert observations(events)[-1]["ok"] is False
    assert [i["number"] for i in report["first_issues"]] == [7, 9]  # fallback, never 999


def test_exploration_budget_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "agent_max_tool_calls", 1)
    steps = [
        reply(call("get_repo_tree", path="")),
        reply(call("list_issues", labels="", limit=5)),
        reply(section("summary")),
        *idle(),
    ]
    _, events = execute(steps)

    obs = observations(events)
    assert obs[0]["ok"] is True
    assert obs[1]["ok"] is False and "budget" in obs[1]["summary"].lower()


def test_unknown_tool_is_a_failed_observation_not_a_crash():
    steps = [reply(call("nope")), reply(section("summary")), *idle()]
    _, events = execute(steps)
    first = observations(events)[0]
    assert first["ok"] is False and "Unknown tool" in first["summary"]


def test_model_that_never_writes_still_gets_a_fallback_report():
    report, _ = execute(idle())
    Report.model_validate(report)
    assert len(report["sections"]) == 5


def test_llm_failure_before_any_section_raises():
    with pytest.raises(LLMError, match="boom"):
        execute([LLMError("boom")])


def test_llm_failure_after_a_section_still_returns_a_report():
    report, _ = execute([reply(section("summary")), LLMError("boom")])
    Report.model_validate(report)
    assert len(report["sections"]) == 5

SYNTH_JSON = json.dumps(
    {
        "summary": "A demo app.",
        "architecture": "Code lives in src/.",
        "diagram": "```mermaid\ngraph TD\n  A-->B\n```",
        "setup": "1. pip install -e .",
        "issues": [
            {"number": 7, "reason": "Touches src/app.py", "difficulty": "easy"},
            {"number": 999, "reason": "made up", "difficulty": "hard"},
        ],
    }
)


def test_synthesis_finishes_the_report_when_the_agent_stalls():
    steps = [
        reply(call("get_repo_tree", path="")),
        *idle(3),
        LLMResponse(text="Here is the report:\n" + SYNTH_JSON),
    ]
    report, events = execute(steps)

    Report.model_validate(report)
    assert [s["key"] for s in report["sections"]] == ["summary", "architecture", "diagram", "setup", "first_issues"]
    assert report["mermaid"] == "graph TD\n  A-->B"
    assert [i["number"] for i in report["first_issues"]] == [7]  # 999 was rejected
    tools = [data["tool"] for event, data in events if event == "tool_call"]
    assert "list_issues" in tools  # the loop looked up issues itself


def test_unusable_synthesis_still_returns_a_fallback_report():
    steps = [
        reply(call("get_repo_tree", path="")),
        *idle(3),
        LLMResponse(text="Sorry, I cannot do that."),
    ]
    report, _ = execute(steps)

    Report.model_validate(report)
    assert report["mermaid"].startswith("graph TD")
    assert [i["number"] for i in report["first_issues"]] == [7, 9]

def test_llm_failure_after_exploring_still_returns_a_fallback_report():
    steps = [
        reply(call("get_repo_tree", path="")),
        LLMError("rate limited"),
        LLMError("rate limited"),
    ]
    report, _ = execute(steps)

    Report.model_validate(report)
    assert report["mermaid"].startswith("graph TD")
    assert len(report["sections"]) == 5