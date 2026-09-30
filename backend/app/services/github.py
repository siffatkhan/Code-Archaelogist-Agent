from urllib.parse import urlparse

import httpx


GITHUB_API = "https://api.github.com"
MAX_FILE_BYTES = 500_000


def parse_github_url(github_url: str) -> tuple[str, str]:
    parsed = urlparse(github_url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise ValueError("Only public HTTPS GitHub repository URLs are supported.")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or any(part in {".", ".."} for part in parts):
        raise ValueError("GitHub URL must look like https://github.com/{owner}/{repository}.")
    return parts[0], parts[1].removesuffix(".git")


async def fetch_repository_metadata(owner: str, name: str) -> dict[str, str]:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(f"{GITHUB_API}/repos/{owner}/{name}")
    if response.status_code == 404:
        raise ValueError("The public GitHub repository was not found.")
    response.raise_for_status()
    payload = response.json()
    return {"default_branch": payload.get("default_branch") or "main"}


async def fetch_file_paths(owner: str, name: str, branch: str) -> list[str]:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(f"{GITHUB_API}/repos/{owner}/{name}/git/trees/{branch}", params={"recursive": "1"})
    response.raise_for_status()
    return [
        item["path"]
        for item in response.json().get("tree", [])
        if item.get("type") == "blob" and isinstance(item.get("path"), str)
    ]


async def fetch_file(owner: str, name: str, branch: str, path: str) -> tuple[str, bool]:
    encoded_path = "/".join(part for part in path.split("/") if part not in {".", ".."})
    url = f"https://raw.githubusercontent.com/{owner}/{name}/{branch}/{encoded_path}"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url)
    response.raise_for_status()
    content = response.content
    truncated = len(content) > MAX_FILE_BYTES
    return content[:MAX_FILE_BYTES].decode("utf-8", errors="replace"), truncated


async def fetch_commits(owner: str, name: str, branch: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(
            f"{GITHUB_API}/repos/{owner}/{name}/commits",
            params={"sha": branch, "per_page": 100},
        )
    response.raise_for_status()
    commits = []
    for item in response.json():
        commit = item.get("commit", {})
        author = commit.get("author") or {}
        commits.append(
            {
                "hash": item.get("sha"),
                "author": author.get("name") or item.get("author", {}).get("login") or "Unknown",
                "message": commit.get("message") or "",
                "timestamp": author.get("date"),
                "url": item.get("html_url"),
            }
        )
    return commits