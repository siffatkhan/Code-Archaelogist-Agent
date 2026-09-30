import logging
from typing import Any

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError, PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .config import get_settings

logger = logging.getLogger(__name__)


PUBLIC_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
PROTECTED_PREFIXES = ("/api/", "/repositories", "/analysis")


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except InvalidTokenError as error:
        raise InvalidTokenError("The access token header is invalid") from error

    if algorithm == settings.supabase_jwt_algorithm:
        if not settings.supabase_jwt_secret:
            raise RuntimeError("SUPABASE_JWT_SECRET is not configured")
        signing_key: Any = settings.supabase_jwt_secret
    elif algorithm in {"ES256", "RS256"} and settings.supabase_url:
        jwks_url = settings.supabase_jwks_url or f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token).key
        except Exception as error:
            raise InvalidTokenError("The Supabase signing key could not be resolved") from error
    else:
        raise InvalidTokenError("The access token uses an unsupported signing algorithm")

    options = {"verify_aud": settings.supabase_jwt_audience is not None}
    return jwt.decode(
        token,
        signing_key,
        algorithms=[algorithm],
        audience=settings.supabase_jwt_audience,
        options=options,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in PUBLIC_PATHS or not request.url.path.startswith(PROTECTED_PREFIXES):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "AUTHENTICATION_REQUIRED", "message": "A Bearer token is required."}},
            )

        try:
            request.state.user = decode_access_token(token)
        except RuntimeError as error:
            return JSONResponse(
                status_code=503,
                content={"error": {"code": "AUTH_CONFIGURATION_ERROR", "message": str(error)}},
            )
        except InvalidTokenError as error:
            logger.warning("Supabase access token rejected: %s", error)
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "INVALID_TOKEN", "message": "The access token is invalid or expired."}},
            )

        return await call_next(request)


def get_current_user(request: Request) -> dict[str, Any]:
    return request.state.user