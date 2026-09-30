from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.routes import router as api_router
from backend.app.api.routes_analysis import router as analysis_router
from backend.app.api.routes_files import router as files_router
from backend.app.api.routes_intelligence import router as intelligence_router
from backend.app.api.routes_repositories import router as repositories_router
from backend.app.api.routes_workspace import router as workspace_router
from backend.app.core.config import get_settings
from backend.app.core.security import AuthMiddleware


settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(repositories_router)
app.include_router(analysis_router)
app.include_router(files_router)
app.include_router(intelligence_router)
app.include_router(workspace_router)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_by_status = {401: "AUTHENTICATION_REQUIRED", 404: "NOT_FOUND", 422: "VALIDATION_ERROR", 502: "UPSTREAM_ERROR"}
    code = code_by_status.get(exc.status_code, "REQUEST_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": message}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "The request contains invalid data."}},
    )


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ok"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}