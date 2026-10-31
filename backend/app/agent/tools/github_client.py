import base64

import httpx

from app.config import settings

API_BASE = "https://api.github.com"


class GitHubError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repopilot-hackathon",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


async def _get(path: str, params: dict | None = None):
    try:
        async with httpx.AsyncClient(
            base_url=API_BASE, headers=_headers(), timeout=20
        ) as client:
            res = await client.get(path, params=params)
    except httpx.HTTPError as exc:
        raise GitHubError(502, "github_unreachable", "Could not reach GitHub.") from exc

    if res.status_code == 404:
        raise GitHubError(404, "not_found", "Not found on GitHub.")
    if res.status_code == 429 or (
        res.status_code == 403 and res.headers.get("x-ratelimit-remaining") == "0"
    ):
        raise GitHubError(429, "rate_limited", "GitHub rate limit reached. Try again later.")
    if res.status_code >= 400:
        raise GitHubError(502, "github_error", f"GitHub returned HTTP {res.status_code}.")
    return res.json()


async def get_repo(owner: str, name: str) -> dict:
    try:
        data = await _get(f"/repos/{owner}/{name}")
    except GitHubError as exc:
        if exc.status == 404:
            raise GitHubError(
                404, "repo_not_found", "Repository not found or not public."
            ) from exc
        raise
    return {
        "default_branch": data.get("default_branch", "main"),
        "description": data.get("description") or "",
        "language": data.get("language") or "",
        "stars": data.get("stargazers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
    }


async def get_tree(owner: str, name: str, branch: str) -> tuple[list[dict], bool]:
    data = await _get(
        f"/repos/{owner}/{name}/git/trees/{branch}", params={"recursive": "1"}
    )
    entries = [
        {"path": e["path"], "size": e.get("size", 0)}
        for e in data.get("tree", [])
        if e.get("type") == "blob"
    ]
    return entries, bool(data.get("truncated"))


async def get_file(owner: str, name: str, path: str) -> dict:
    data = await _get(f"/repos/{owner}/{name}/contents/{path}")
    if isinstance(data, list):
        raise GitHubError(400, "is_directory", f"{path} is a directory. Use get_repo_tree.")
    if data.get("encoding") != "base64" or not data.get("content"):
        raise GitHubError(400, "unreadable_file", f"{path} is too large to read.")
    raw = base64.b64decode(data["content"])
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitHubError(400, "binary_file", f"{path} looks like a binary file.") from exc
    return {"text": text, "size": data.get("size", len(raw))}


async def search_code(owner: str, name: str, query: str) -> list[str]:
    data = await _get(
        "/search/code", params={"q": f"{query} repo:{owner}/{name}", "per_page": 10}
    )
    return [item["path"] for item in data.get("items", [])]


async def list_issues(
    owner: str, name: str, labels: str | None = None, per_page: int = 30
) -> list[dict]:
    params = {"state": "open", "per_page": per_page, "sort": "updated"}
    if labels:
        params["labels"] = labels
    return await _get(f"/repos/{owner}/{name}/issues", params=params)