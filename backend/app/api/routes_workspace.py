from pathlib import PurePosixPath
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.routes_repositories import user_id
from backend.app.services.repository_store import RepositoryRecord, repository_store

router = APIRouter(prefix="/repositories/{repository_id}", tags=["workspace"])


def repository_for_user(repository_id: UUID, current_user: str) -> RepositoryRecord:
    record = repository_store.get_for_user(current_user, repository_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repository was not found.")
    return record


@router.get("/history")
async def get_history(repository_id: UUID, current_user: str = Depends(user_id)) -> dict:
    record = repository_for_user(repository_id, current_user)
    return {"commits": record.commits}


@router.get("/architecture")
async def get_architecture(repository_id: UUID, current_user: str = Depends(user_id)) -> dict:
    record = repository_for_user(repository_id, current_user)
    nodes = []
    edges = []
    seen_directories: set[str] = set()
    for path in record.files:
        parts = PurePosixPath(path).parts
        parent = ""
        for part in parts[:-1]:
            directory = f"{parent}/{part}".strip("/")
            if directory not in seen_directories:
                seen_directories.add(directory)
                nodes.append({"id": f"dir:{directory}", "label": part, "path": directory, "type": "directory", "entity_count": 0})
                if parent:
                    edges.append({"source": f"dir:{parent}", "target": f"dir:{directory}", "type": "contains"})
            parent = directory
        file_id = f"file:{path}"
        nodes.append({"id": file_id, "label": parts[-1], "path": path, "type": "file", "entity_count": len(record.entities.get(path, []))})
        if parent:
            edges.append({"source": f"dir:{parent}", "target": file_id, "type": "contains"})
    return {"nodes": nodes, "edges": edges}