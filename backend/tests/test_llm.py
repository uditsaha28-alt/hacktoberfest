import asyncio
import json

import pytest

from app.agent.llm.base import LLMClient, LLMError, LLMResponse, clean_schema
from app.agent.llm.factory import FallbackLLM, build_llm
from app.agent.llm.gemini import parse_response as gemini_parse
from app.agent.llm.gemini import to_contents
from app.agent.llm.groq import parse_response as groq_parse
from app.agent.llm.groq import to_messages
from app.agent.tools.registry import TOOL_SCHEMAS
from app.config import settings


def run(coro):
    return asyncio.run(coro)


def has_empty_required(node):
    if isinstance(node, dict):
        if "required" in node and not node["required"]:
            return True
        return any(has_empty_required(v) for v in node.values())
    if isinstance(node, list):
        return any(has_empty_required(v) for v in node)
    return False


class Stub(LLMClient):
    def __init__(self, name, result=None, error=None):
        self.name = name
        self.result = result
        self.error = error
        self.calls = 0

    async def generate(self, system, history, tools):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def test_clean_schema_drops_only_empty_required():
    schema = {"type": "object", "required": [], "properties": {"a": {"type": "string"}}}
    assert "required" not in clean_schema(schema)
    keep = {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}
    assert clean_schema(keep) == keep


def test_all_tool_schemas_are_clean_after_cleaning():
    assert any(has_empty_required(s["parameters"]) for s in TOOL_SCHEMAS)  # cleaning matters
    assert not any(has_empty_required(clean_schema(s["parameters"])) for s in TOOL_SCHEMAS)


def test_gemini_contents_reuse_raw_parts_and_ids():
    raw_parts = [
        {
            "functionCall": {"name": "read_file", "args": {"path": "README.md"}, "id": "g1"},
            "thoughtSignature": "sig123",
        }
    ]
    history = [
        {"role": "user", "content": "go"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "t1", "name": "read_file", "args": {"path": "README.md"}, "provider_id": "g1"}],
            "gemini_parts": raw_parts,
        },
        {"role": "tool", "results": [{"id": "t1", "name": "read_file", "provider_id": "g1", "result": {"ok": True}}]},
    ]
    contents = to_contents(history)
    assert contents[0] == {"role": "user", "parts": [{"text": "go"}]}
    assert contents[1] == {"role": "model", "parts": raw_parts}
    assert contents[2]["parts"][0]["functionResponse"] == {
        "name": "read_file",
        "response": {"ok": True},
        "id": "g1",
    }


def test_gemini_contents_build_from_neutral_messages():
    history = [
        {"role": "assistant", "content": "hi", "tool_calls": [{"id": "t1", "name": "list_issues", "args": {}}]},
        {"role": "assistant", "content": "", "tool_calls": []},
    ]
    contents = to_contents(history)
    assert contents[0]["parts"] == [{"text": "hi"}, {"functionCall": {"name": "list_issues", "args": {}}}]
    assert contents[1]["parts"] == [{"text": "(no output)"}]


def test_gemini_parse_function_call_keeps_raw_parts():
    parts = [
        {"text": "Looking."},
        {"functionCall": {"name": "get_repo_tree", "args": {"path": ""}}, "thoughtSignature": "abc"},
    ]
    resp = gemini_parse({"candidates": [{"content": {"parts": parts}}]})
    assert resp.text == "Looking."
    assert resp.tool_calls[0].name == "get_repo_tree"
    assert resp.tool_calls[0].args == {"path": ""}
    assert resp.gemini_parts == parts


def test_gemini_parse_empty_candidates_raises():
    with pytest.raises(LLMError):
        gemini_parse({"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}})


def test_groq_messages_conversion():
    history = [
        {"role": "user", "content": "go"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t1", "name": "read_file", "args": {"path": "README.md"}}]},
        {"role": "tool", "results": [{"id": "t1", "name": "read_file", "result": {"ok": True}}]},
    ]
    msgs = to_messages("sys", history)
    assert msgs[0] == {"role": "system", "content": "sys"}
    call = msgs[2]["tool_calls"][0]
    assert call["id"] == "t1"
    assert json.loads(call["function"]["arguments"]) == {"path": "README.md"}
    assert msgs[3]["tool_call_id"] == "t1"
    assert json.loads(msgs[3]["content"]) == {"ok": True}


def test_groq_parse_handles_bad_arguments():
    data = {
        "choices": [
            {"message": {"content": None, "tool_calls": [
                {"id": "abc", "type": "function", "function": {"name": "read_file", "arguments": "{not json"}}
            ]}}
        ]
    }
    resp = groq_parse(data)
    assert resp.tool_calls[0].args == {}
    assert resp.text == ""


def test_fallback_switches_and_sticks():
    a = Stub("a", error=LLMError("down"))
    b = Stub("b", result=LLMResponse(text="ok"))
    llm = FallbackLLM([a, b])
    assert run(llm.generate("s", [], [])).text == "ok"
    assert llm.name == "b"
    run(llm.generate("s", [], []))
    assert a.calls == 1 and b.calls == 2


def test_fallback_all_fail_raises():
    llm = FallbackLLM([Stub("a", error=LLMError("x")), Stub("b", error=LLMError("y"))])
    with pytest.raises(LLMError):
        run(llm.generate("s", [], []))


def test_build_llm_requires_a_provider(monkeypatch):
    for field in ("gemini_api_key", "gemini_model", "groq_api_key", "groq_model"):
        monkeypatch.setattr(settings, field, "")
    with pytest.raises(LLMError):
        build_llm()


def test_build_llm_orders_gemini_before_groq(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "k1")
    monkeypatch.setattr(settings, "gemini_model", "m1")
    monkeypatch.setattr(settings, "groq_api_key", "k2")
    monkeypatch.setattr(settings, "groq_model", "m2")
    llm = build_llm()
    assert [c.name for c in llm.clients] == ["gemini", "groq"]

def test_standalone_ignores_the_sticky_fallback():
    a = Stub("a", error=LLMError("down"))
    b = Stub("b", result=LLMResponse(text="ok"))
    llm = FallbackLLM([a, b])
    run(llm.generate("s", [], []))  # a fails, the llm now sticks to b
    a.error = None
    a.result = LLMResponse(text="from a")
    assert run(llm.generate_standalone("s", [], [])).text == "from a"

def test_standalone_uses_its_own_chain_order():
    a = Stub("a", error=LLMError("down"))
    extra = Stub("extra", result=LLMResponse(text="from extra"))
    b = Stub("b", result=LLMResponse(text="from b"))
    llm = FallbackLLM([a, b], standalone=[a, extra, b])
    assert run(llm.generate_standalone("s", [], [])).text == "from extra"