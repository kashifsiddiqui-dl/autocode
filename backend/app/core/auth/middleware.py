"""Authentication and tenant middleware for FastAPI."""

from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import verify_token
from app.core.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)

# Paths that do not require authentication.
_PUBLIC_PATHS: set[str] = {
    "/api/v1/health",
    "/api/v1/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Extract and validate JWT from the Authorization header or cookie.

    On success, sets ``request.state.user_id``, ``request.state.tenant_id``,
    and ``request.state.role``.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path.rstrip("/")
        if path in _PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        token = self._extract_token(request)
        if token is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authentication token."},
            )

        try:
            payload = verify_token(token)
        except UnauthorizedError:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token."},
            )

        if payload.token_type != "access":
            return JSONResponse(
                status_code=401,
                content={"detail": "Token type is not valid for this endpoint."},
            )

        request.state.user_id = uuid.UUID(payload.sub)
        request.state.tenant_id = uuid.UUID(payload.tenant_id)
        request.state.role = payload.role
        return await call_next(request)

    @staticmethod
    def _extract_token(request: Request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        return request.cookies.get("access_token")


class TenantMiddleware(BaseHTTPMiddleware):
    """Set the PostgreSQL session variable for row-level security.

    Must be added *after* AuthMiddleware so ``request.state.tenant_id`` is
    available.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
        if tenant_id is not None:
            # Store for later use by the DB session dependency.
            request.state.rls_tenant_id = str(tenant_id)
        return await call_next(request)
