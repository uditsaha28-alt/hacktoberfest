from typing import Any, Awaitable, Callable

from app.agent.tools import github_client

Publish = Callable[[str, dict[str, Any]], Awaitable[None]]

IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", "vendor", "__pycache__",
    ".venv", "venv", "target", ".next", "coverage",
}
IGNORED_NAMES = {"package-lock.json"}
IGNORED_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".pdf", ".zip", ".gz",
    ".mp4", ".mp3", ".lock", ".min.js", ".map",
)


def is_ignored(path: str) -> bool:
    parts = path.split("/")
    if any(p in IGNORED_DIRS for p in parts[:-1]):
        return True
    filename = parts[-1]
    return filename in IGNORED_NAMES or filename.lower().endswith(IGNORED_SUFFIXES)


class ToolContext:
    def __init__(self, owner: str, name: str, publish: Publish) -> None:
        self.owner = owner
        self.name = name
        self.publish = publish
        self.default_branch: str | None = None
        self.repo_info: dict = {}
        self.tree_truncated = False
        self.sections: dict[str, dict] = {}
        self.issues_seen: dict[int, dict] = {}
        self._tree: list[dict] | None = None

    async def load_repo(self) -> None:
        if self.default_branch is None:
            self.repo_info = await github_client.get_repo(self.owner, self.name)
            self.default_branch = self.repo_info["default_branch"]

    async def get_tree(self) -> list[dict]:
        if self._tree is None:
            await self.load_repo()
            entries, truncated = await github_client.get_tree(
                self.owner, self.name, self.default_branch
            )
            self.tree_truncated = truncated
            self._tree = [e for e in entries if not is_ignored(e["path"])]
        return self._tree