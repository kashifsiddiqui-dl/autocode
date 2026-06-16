"""FastAPI application factory and lifespan management."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text as sa_text

from app.config import settings
from app.core.exceptions import AutoCodeException
from app.core.middleware import AuditMiddleware, RequestIDMiddleware
from app.db.session import engine
from app.db.vector import qdrant_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise shared resources on startup; tear them down on shutdown."""
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting %s ...", settings.APP_NAME)

    # Verify the async DB engine is reachable
    async with engine.begin() as conn:
        await conn.execute(sa_text("SELECT 1"))
    logger.info("PostgreSQL connection verified")

    # Connect to Qdrant and ensure collections exist
    await qdrant_manager.connect()
    await qdrant_manager.init_collections()
    logger.info("Qdrant initialised")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await qdrant_manager.close()
    await engine.dispose()
    logger.info("%s shut down cleanly", settings.APP_NAME)


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # ── Middleware (outermost first) ──────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(AuditMiddleware)

    # ── Exception handlers ───────────────────────────────────────────────────
    @app.exception_handler(AutoCodeException)
    async def autocode_exception_handler(
        request: Request,
        exc: AutoCodeException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": type(exc).__name__, "message": exc.detail}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "InternalServerError", "message": "An internal error occurred."}},
        )

    # ── Routers ──────────────────────────────────────────────────────────────
    from app.api.v1.router import v1_router

    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
