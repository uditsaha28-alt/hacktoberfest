ALLOWED_KEYS = ("summary", "architecture", "diagram", "setup", "first_issues")


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rstrip()
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


async def write_section(ctx, key: str, title: str, markdown: str) -> dict:
    if key not in ALLOWED_KEYS:
        return {
            "ok": False,
            "summary": f"Invalid section key '{key}'. Use one of: {', '.join(ALLOWED_KEYS)}",
            "data": {},
        }
    body = _strip_fences(markdown) if key == "diagram" else markdown.strip()
    section = {"key": key, "title": title, "markdown": body}
    ctx.sections[key] = section
    await ctx.publish("section", section)
    return {"ok": True, "summary": f"Wrote section '{title}'", "data": {}}