import re

_PATTERN = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def parse_repo_url(url: str) -> tuple[str, str]:
    match = _PATTERN.match(url.strip())
    if not match:
        raise ValueError("Repo URL must look like https://github.com/owner/name")
    return match.group(1), match.group(2)