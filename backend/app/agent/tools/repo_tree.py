MAX_FILES_LISTED = 80


async def get_repo_tree(ctx, path: str = "") -> dict:
    tree = await ctx.get_tree()
    prefix = path.strip("/")
    if prefix == ".":
        prefix = ""
    prefix = f"{prefix}/" if prefix else ""

    dir_counts: dict[str, int] = {}
    files: list[str] = []
    for entry in tree:
        p = entry["path"]
        if not p.startswith(prefix):
            continue
        rest = p[len(prefix):]
        if "/" in rest:
            top = rest.split("/", 1)[0]
            dir_counts[top] = dir_counts.get(top, 0) + 1
        else:
            files.append(rest)

    if not dir_counts and not files:
        return {"ok": False, "summary": f"Path not found: {path or '/'}", "data": {}}

    files.sort()
    directories = [{"name": n, "files": c} for n, c in sorted(dir_counts.items())]
    where = prefix.rstrip("/") or "repo root"
    summary = f"Listed {where}: {len(directories)} folders, {len(files)} files"
    if ctx.tree_truncated:
        summary += " (GitHub truncated this tree)"
    return {
        "ok": True,
        "summary": summary,
        "data": {
            "path": prefix.rstrip("/"),
            "directories": directories,
            "files": files[:MAX_FILES_LISTED],
            "truncated": len(files) > MAX_FILES_LISTED,
        },
    }