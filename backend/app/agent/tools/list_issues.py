from app.agent.tools import github_client


async def list_issues(ctx, labels: str = "", limit: int = 15) -> dict:
    limit = max(1, min(int(limit), 30))
    raw = await github_client.list_issues(
        ctx.owner, ctx.name, labels=labels or None, per_page=min(limit * 2, 60)
    )
    issues = []
    for item in raw:
        if "pull_request" in item:
            continue
        issue = {
            "number": item["number"],
            "title": item["title"],
            "url": item["html_url"],
            "labels": [lbl["name"] for lbl in item.get("labels", [])],
            "body": (item.get("body") or "")[:300],
        }
        ctx.issues_seen[issue["number"]] = issue
        issues.append(issue)
        if len(issues) >= limit:
            break
    return {
        "ok": True,
        "summary": f"Found {len(issues)} open issues",
        "data": {"issues": issues},
    }