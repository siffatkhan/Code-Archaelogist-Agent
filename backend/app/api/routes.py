from typing import Any

from fastapi import APIRouter, Depends

from backend.app.core.security import get_current_user

router = APIRouter(prefix="/api/v1")


@router.get("/me")
async def read_current_user(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": user}