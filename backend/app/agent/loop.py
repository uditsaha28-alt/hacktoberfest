import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.agent.llm.base import LLMClient, LLMError, ToolCall
from app.agent.llm.factory import build_llm
from app.agent.tools.context import ToolContext
from app.agent.tools.registry import TOOL_SCHEMAS, execute_tool
from app.agent.tools.write_section import ALLOWED_KEYS, _strip_fences
from app.config import settings
from app.services.repo_url import parse_repo_url

logger = logging.getLogger(__name__)

Publish = Callable[[str, dict[str, Any]], Awaitable[None]]

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"
EXPLORATION_TOOLS = {"get_repo_tree", "read_file", "search_code", "list_issues"}
SECTION_TITLES = {
    "summary": "Overview",
    "architecture": "Architecture",
    "diagram": "Diagram",
    "setup": "Local setup",
    "first_issues": "First contributions",
}
DEFAULT_PLAN = [
    "Explore the repository structure",
    "Read the README and key source files",
    "Check open issues for newcomers",
    "Write the onboarding report",
]

CONTROL_SCHEMAS = [
    {
        "name": "update_plan",
        "description": "Show the user your current plan as 4-6 short steps. Call it first, and again whenever the plan changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {"type": "array", "items": {"type": "string"}, "description": "Short plan steps."}
            },
            "required": ["steps"],
        },
    },
    {
        "name": "submit_first_issues",
        "description": "Submit the 3-5 best first-contribution issues, best first. Only use numbers returned by list_issues.",
        "parameters": {
            "type": "object",
            "properties": {
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {"type": "integer"},
                            "reason": {"type": "string"},
                            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                        },
                        "required": ["number", "reason", "difficulty"],
                    },
                }
            },
            "required": ["issues"],
        },
    },
]

SYNTH_SYSTEM = (
    "You write onboarding reports for first-time contributors to a GitHub repository. "
    "Use ONLY the notes provided. Never invent files, folders, commands or issue numbers. "
    "Reply with a single JSON object and nothing else."
)


class RunState:
    def __init__(self) -> None:
        self.counter = 0
        self.used = 0
        self.issues: list[dict] = []
        self.notes: list[str] = []
        self.pending: set[str] = set()
        self.issues_checked = False

    def next_id(self) -> str:
        self.counter += 1
        return f"t{self.counter}"


def _display_args(name: str, args: dict) -> dict:
    if name == "write_section":
        return {k: args[k] for k in ("key", "title") if k in args}
    return {k: (v[:120] if isinstance(v, str) else v) for k, v in args.items()}


def _note(name: str, result: dict) -> str:
    """Compact text kept for the final synthesis step."""
    data = result.get("data") or {}
    if name == "get_repo_tree":
        dirs = ", ".join(f"{d['name']}/ ({d['files']} files)" for d in data.get("directories", []))
        files = ", ".join(data.get("files", []))
        return f"TREE of /{data.get('path', '')}\nfolders: {dirs or 'none'}\nfiles: {files or 'none'}"
    if name == "read_file":
        return f"FILE {data.get('path')}:\n{str(data.get('content', ''))[:2500]}"
    if name == "search_code":
        return f"SEARCH '{data.get('query')}': " + ", ".join(data.get("paths", []))
    if name == "list_issues":
        lines = [
            f"#{i['number']} {i['title']} [{', '.join(i['labels'])}] {i['body'][:150].replace(chr(10), ' ')}"
            for i in data.get("issues", [])
        ]
        return "OPEN ISSUES:\n" + ("\n".join(lines) or "none")
    return ""


def _submit_issues(ctx: ToolContext, state: RunState, args: dict) -> dict:
    accepted: list[dict] = []
    rejected = 0
    for item in args.get("issues") or []:
        if not isinstance(item, dict):
            continue
        try:
            number = int(item.get("number"))
        except (TypeError, ValueError):
            rejected += 1
            continue
        seen = ctx.issues_seen.get(number)
        if seen is None or any(a["number"] == number for a in accepted):
            rejected += 1
            continue
        difficulty = item.get("difficulty")
        accepted.append(
            {
                "number": number,
                "title": seen["title"],
                "url": seen["url"],
                "reason": str(item.get("reason") or "").strip() or "Open issue that matches this repository.",
                "difficulty": difficulty if difficulty in ("easy", "medium", "hard") else "medium",
            }
        )
    if not accepted:
        return {
            "ok": False,
            "summary": "None of those issue numbers came from list_issues. Call list_issues first and use its numbers.",
            "data": {},
        }
    state.issues = accepted[:5]
    note = f" (ignored {rejected} unknown)" if rejected else ""
    return {"ok": True, "summary": f"Recorded {len(state.issues)} first issues{note}", "data": {}}


async def _run_tool(
    ctx: ToolContext, state: RunState, call: ToolCall, publish: Publish, force: bool = False
) -> dict:
    name = call.name
    args = call.args if isinstance(call.args, dict) else {}

    if name == "update_plan":
        steps = [str(s).strip() for s in (args.get("steps") or []) if str(s).strip()][:8]
        if not steps:
            return {"ok": False, "summary": "Plan was empty.", "data": {}}
        await publish("plan", {"steps": steps})
        return {"ok": True, "summary": "Plan updated.", "data": {}}

    await publish("tool_call", {"id": call.id, "tool": name, "args": _display_args(name, args)})
    state.pending.add(call.id)

    if name == "submit_first_issues":
        result = _submit_issues(ctx, state, args)
    elif name in EXPLORATION_TOOLS and not force and state.used >= settings.agent_max_tool_calls:
        result = {
            "ok": False,
            "summary": "Exploration budget used up. Write the remaining sections now.",
            "data": {},
        }
    else:
        if name in EXPLORATION_TOOLS and not force:
            state.used += 1
        if name == "list_issues":
            state.issues_checked = True
        result = await execute_tool(ctx, name, args)
        if result.get("ok") and name in EXPLORATION_TOOLS:
            note = _note(name, result)
            if note:
                state.notes.append(note)

    if name in EXPLORATION_TOOLS:
        result["budget_remaining"] = max(0, settings.agent_max_tool_calls - state.used)

    await publish(
        "observation",
        {"id": call.id, "ok": bool(result.get("ok")), "summary": str(result.get("summary", ""))},
    )
    state.pending.discard(call.id)
    return result


async def _close_pending(state: RunState, publish: Publish) -> None:
    for call_id in sorted(state.pending):
        await publish("observation", {"id": call_id, "ok": False, "summary": "Stopped: time limit reached."})
    state.pending.clear()


def _intro(ctx: ToolContext) -> str:
    info = ctx.repo_info
    return (
        f"Repository: {ctx.owner}/{ctx.name}\n"
        f"Description: {info.get('description') or 'none'}\n"
        f"Primary language: {info.get('language') or 'unknown'}\n"
        f"Stars: {info.get('stars', 0)}\n"
        f"Open issues (including PRs): {info.get('open_issues', 0)}\n\n"
        "A default plan is already shown to the user. Start by calling update_plan with your own plan for this repository."
    )


async def _explore(
    llm: LLMClient,
    ctx: ToolContext,
    state: RunState,
    system: str,
    schemas: list[dict],
    history: list[dict],
    publish: Publish,
) -> None:
    nudges = 0
    for turn in range(1, settings.agent_max_tool_calls + 12):
        started = time.monotonic()
        response = await llm.generate(system, history, schemas)
        elapsed = time.monotonic() - started
        logger.info(
            "Agent turn %d: %.1fs, %d tool calls, %d chars of text",
            turn, elapsed, len(response.tool_calls), len(response.text),
        )
        if elapsed > 20:
            logger.warning("Slow LLM turn: %.1fs", elapsed)

        if not response.tool_calls:
            if not response.text.strip():
                logger.warning("Model returned an empty reply (turn %d)", turn)
            missing = [k for k in ALLOWED_KEYS if k not in ctx.sections]
            if missing and nudges < 2:
                nudges += 1
                history.append(
                    {
                        "role": "assistant",
                        "content": response.text,
                        "tool_calls": [],
                        "gemini_parts": response.gemini_parts,
                    }
                )
                history.append(
                    {
                        "role": "user",
                        "content": "You have not written these sections yet: "
                        + ", ".join(missing)
                        + ". Write them now with write_section using what you learned, then call submit_first_issues.",
                    }
                )
                continue
            return

        for call in response.tool_calls:
            call.id = state.next_id()
        history.append(
            {
                "role": "assistant",
                "content": response.text,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "args": c.args, "provider_id": c.provider_id}
                    for c in response.tool_calls
                ],
                "gemini_parts": response.gemini_parts,
            }
        )
        results = []
        for call in response.tool_calls:
            result = await _run_tool(ctx, state, call, publish)
            results.append(
                {"id": call.id, "name": call.name, "provider_id": call.provider_id, "result": result}
            )
        history.append({"role": "tool", "results": results})


async def _ensure_issues(ctx: ToolContext, state: RunState, publish: Publish) -> None:
    if ctx.issues_seen or state.issues_checked:
        return
    for labels in ("good first issue", ""):
        call = ToolCall(name="list_issues", args={"labels": labels, "limit": 10}, id=state.next_id())
        await _run_tool(ctx, state, call, publish, force=True)
        if ctx.issues_seen:
            break


def _extract_json(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


async def _synthesize(llm: LLMClient, ctx: ToolContext, state: RunState) -> None:
    """Safety net: turn the gathered notes into the report in ONE call, without tools."""
    digest = "\n\n".join(state.notes)[:9000]
    if not digest:
        return
    info = ctx.repo_info
    prompt = (
        f"Repository: {ctx.owner}/{ctx.name}\n"
        f"Description: {info.get('description') or 'none'}\n"
        f"Primary language: {info.get('language') or 'unknown'}\n\n"
        f"NOTES FROM EXPLORATION:\n{digest}\n\n"
        "Write the report as ONE JSON object with exactly these keys:\n"
        '- "summary": 2-4 sentences: what the project is, who it is for, main language and stack.\n'
        '- "architecture": under 200 words on the main folders/modules and how they fit together. Name real paths from the notes.\n'
        '- "diagram": raw Mermaid source starting with "graph TD", at most 10 nodes, node ids like A or B1, '
        'labels written as A["text"] with no parentheses or colons. No code fences.\n'
        '- "setup": numbered install-and-run steps taken from the notes. If they are not in the notes, say so.\n'
        '- "issues": up to 4 objects {"number", "reason", "difficulty"} chosen ONLY from the OPEN ISSUES in the notes, '
        "best first, difficulty easy/medium/hard. Use an empty list if there are none.\n"
        "Return only the JSON."
    )
    generate = getattr(llm, "generate_standalone", llm.generate)
    response = await generate(SYNTH_SYSTEM, [{"role": "user", "content": prompt}], [])
    data = _extract_json(response.text)
    if data is None:
        logger.warning("Synthesis returned no usable JSON")
        return
    for key in ("summary", "architecture", "diagram", "setup"):
        if key in ctx.sections:
            continue
        text = data.get(key)
        if not isinstance(text, str) or not text.strip():
            continue
        body = _strip_fences(text) if key == "diagram" else text.strip()
        section = {"key": key, "title": SECTION_TITLES[key], "markdown": body}
        ctx.sections[key] = section
        await ctx.publish("section", section)
    if not state.issues and isinstance(data.get("issues"), list):
        _submit_issues(ctx, state, {"issues": data["issues"]})


def _issues_markdown(issues: list[dict]) -> str:
    if not issues:
        return "No open issues were found for this repository."
    return "\n".join(
        f"- [#{i['number']} {i['title']}]({i['url']}) ({i['difficulty']}): {i['reason']}" for i in issues
    )


def _fallback_issues(ctx: ToolContext) -> list[dict]:
    return [
        {
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["url"],
            "reason": "Open issue. Read its description to judge the scope.",
            "difficulty": "medium",
        }
        for issue in list(ctx.issues_seen.values())[:3]
    ]


def _fallback_mermaid(ctx: ToolContext, tree: list[dict]) -> str:
    dirs = sorted({e["path"].split("/")[0] for e in tree if "/" in e["path"]})[:8]
    label = ctx.name.replace('"', "")
    lines = ["graph TD", f'  R["{label}"]']
    for i, directory in enumerate(dirs):
        lines.append(f'  R --> D{i}["{directory.replace(chr(34), "")}"]')
    return "\n".join(lines)


async def _build_report(ctx: ToolContext, state: RunState) -> dict:
    try:
        tree = await ctx.get_tree()
    except Exception:
        tree = []
    issues = state.issues or _fallback_issues(ctx)
    fallbacks = {
        "summary": ctx.repo_info.get("description") or f"{ctx.owner}/{ctx.name}",
        "architecture": "The agent did not finish describing the architecture. See the diagram for the folder layout and the README for details.",
        "diagram": _fallback_mermaid(ctx, tree),
        "setup": "The agent did not finish the setup guide. Check the README and the project manifest for install and run instructions.",
        "first_issues": _issues_markdown(issues),
    }
    for key in ALLOWED_KEYS:
        if key not in ctx.sections:
            section = {"key": key, "title": SECTION_TITLES[key], "markdown": fallbacks[key]}
            ctx.sections[key] = section
            await ctx.publish("section", section)
    return {
        "repo": f"{ctx.owner}/{ctx.name}",
        "summary": ctx.sections["summary"]["markdown"],
        "sections": [ctx.sections[key] for key in ALLOWED_KEYS],
        "mermaid": ctx.sections["diagram"]["markdown"],
        "first_issues": issues,
    }


async def run_agent(repo_url: str, publish: Publish, llm: LLMClient | None = None) -> dict:
    owner, name = parse_repo_url(repo_url)
    ctx = ToolContext(owner, name, publish)
    llm = llm or build_llm()
    await ctx.load_repo()  # raises GitHubError for missing or private repos

    state = RunState()
    system = PROMPT_PATH.read_text(encoding="utf-8").replace(
        "{{MAX_CALLS}}", str(settings.agent_max_tool_calls)
    )
    schemas = TOOL_SCHEMAS + CONTROL_SCHEMAS
    history: list[dict] = [{"role": "user", "content": _intro(ctx)}]

    await publish("plan", {"steps": list(DEFAULT_PLAN)})

    llm_error: LLMError | None = None
    try:
        async with asyncio.timeout(settings.agent_timeout_seconds):
            await _explore(llm, ctx, state, system, schemas, history, publish)
    except TimeoutError:
        logger.warning("Agent hit the time limit; moving on to the final report")
        await _close_pending(state, publish)
    except LLMError as exc:
        logger.warning("LLM failed during exploration: %s", exc)
        llm_error = exc
        await _close_pending(state, publish)

    gathered = len(state.notes)  # what exploration collected, before the safety net runs

    if any(key not in ctx.sections for key in ALLOWED_KEYS):
        try:
            async with asyncio.timeout(settings.agent_synthesis_seconds):
                await _ensure_issues(ctx, state, publish)
                await _synthesize(llm, ctx, state)
        except TimeoutError:
            logger.warning("Synthesis timed out")
            await _close_pending(state, publish)
        except LLMError as exc:
            logger.warning("Synthesis failed: %s", exc)
            await _close_pending(state, publish)

    if not ctx.sections and gathered == 0 and llm_error is not None:
        raise llm_error
    return await _build_report(ctx, state)