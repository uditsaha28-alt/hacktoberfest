from app.agent.tools import github_client

MAX_CHARS = 6000


async def read_file(ctx, path: str) -> dict:
    clean = path.strip("/")
    data = await github_client.get_file(ctx.owner, ctx.name, clean)
    text = data["text"]
    truncated = len(text) > MAX_CHARS
    if truncated:
        text = text[:MAX_CHARS]
    note = ", truncated" if truncated else ""
    return {
        "ok": True,
        "summary": f"Read {clean} ({data['size'] / 1024:.1f} KB{note})",
        "data": {"path": clean, "content": text, "truncated": truncated},
    }