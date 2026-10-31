from app.agent.tools import github_client
from app.agent.tools.github_client import GitHubError


async def search_code(ctx, query: str) -> dict:
    q = query.strip()
    if not q:
        return {"ok": False, "summary": "Search query is empty.", "data": {}}

    tree = await ctx.get_tree()
    low = q.lower()
    path_hits = [e["path"] for e in tree if low in e["path"].lower()][:10]

    content_hits: list[str] = []
    try:
        content_hits = await github_client.search_code(ctx.owner, ctx.name, q)
    except GitHubError:
        pass  # content search is best effort

    paths = list(dict.fromkeys(path_hits + content_hits))[:15]
    return {
        "ok": True,
        "summary": f"Found {len(paths)} files matching '{q}'",
        "data": {"query": q, "paths": paths},
    }