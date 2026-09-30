from pathlib import PurePosixPath
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.routes_repositories import user_id
from backend.app.schemas.repositories import FileContentResponse, FileNode
from backend.app.services.github import fetch_file
from backend.app.services.repository_store import repository_store

router = APIRouter(prefix="/repositories/{repository_id}/files", tags=["files"])


def language_for(path: str) -> str | None:
    suffix = PurePosixPath(path).suffix.lower()
    return {".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript", ".java": "java", ".go": "go", ".cpp": "cpp", ".h": "cpp"}.get(suffix)


def build_tree(paths: list[str]) -> list[FileNode]:
    root: dict[str, object] = {}
    for path in paths:
        current = root
        parts = path.split("/")
        for part in parts[:-1]:
            current = current.setdefault(part, {})  # type: ignore[assignment]
        current[parts[-1]] = None

    def convert(node: dict[str, object], prefix: str = "") -> list[FileNode]:
        result: list[FileNode] = []
        for name in sorted(node):
            path = f"{prefix}/{name}".lstrip("/")
            child = node[name]
            if child is None:
                result.append(FileNode(path=path, name=name, type="file"))
            else:
                result.append(FileNode(path=path, name=name, type="directory", children=convert(child, path)))  # type: ignore[arg-type]
        return result

    return convert(root)


@router.get("", response_model=list[FileNode])
async def get_file_tree(repository_id: UUID, current_user: str = Depends(user_id)) -> list[FileNode]:
    record = repository_store.get_for_user(current_user, repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return build_tree(record.files)


@router.get("/{path:path}", response_model=FileContentResponse)
async def get_file_content(repository_id: UUID, path: str, current_user: str = Depends(user_id)) -> FileContentResponse:
    record = repository_store.get_for_user(current_user, repository_id)
    if not record or path not in record.files or not record.default_branch:
        raise HTTPException(status_code=404, detail="File was not found.")
    try:
        content, truncated = await fetch_file(record.owner, record.name, record.default_branch, path)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Could not retrieve the file from GitHub.") from error
    return FileContentResponse(path=path, content=content, language=language_for(path), size_bytes=len(content.encode()), truncated=truncated)