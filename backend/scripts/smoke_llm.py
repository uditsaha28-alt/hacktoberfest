import asyncio

from app.agent.llm.factory import build_llm
from app.agent.tools.registry import TOOL_SCHEMAS

SYSTEM = "You explore GitHub repositories using the tools you are given."


async def main() -> None:
    llm = build_llm()
    history = [
        {
            "role": "user",
            "content": "List the files in the root of the repo with your tool, then tell me how many files you saw.",
        }
    ]

    first = await llm.generate(SYSTEM, history, TOOL_SCHEMAS)
    print(f"[{llm.name}] turn 1 text: {first.text!r}")
    print("turn 1 tool calls:", [(c.name, c.args) for c in first.tool_calls])
    if not first.tool_calls:
        print("WARNING: the model did not call a tool")
        return

    for i, call in enumerate(first.tool_calls, 1):
        call.id = f"t{i}"
    history.append(
        {
            "role": "assistant",
            "content": first.text,
            "tool_calls": [
                {"id": c.id, "name": c.name, "args": c.args, "provider_id": c.provider_id}
                for c in first.tool_calls
            ],
            "gemini_parts": first.gemini_parts,
        }
    )
    fake_result = {
        "ok": True,
        "summary": "Listed repo root: 1 folders, 2 files",
        "data": {"directories": [{"name": "src", "files": 5}], "files": ["README.md", "setup.py"]},
    }
    history.append(
        {
            "role": "tool",
            "results": [
                {"id": c.id, "name": c.name, "provider_id": c.provider_id, "result": fake_result}
                for c in first.tool_calls
            ],
        }
    )

    second = await llm.generate(SYSTEM, history, TOOL_SCHEMAS)
    print(f"[{llm.name}] turn 2 text: {second.text!r}")
    print("turn 2 tool calls:", [(c.name, c.args) for c in second.tool_calls])


if __name__ == "__main__":
    asyncio.run(main())