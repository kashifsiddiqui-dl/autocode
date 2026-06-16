"""Aggregate all v1 endpoint routers into a single router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.codes import router as codes_router
from app.api.v1.endpoints.coding import router as coding_router
from app.api.v1.endpoints.exports import router as exports_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.patients import router as patients_router
from app.api.v1.endpoints.sessions import router as sessions_router
from app.api.v1.endpoints.standards import router as standards_router

v1_router = APIRouter()

# Public
v1_router.include_router(health_router)

# Authenticated
v1_router.include_router(coding_router, prefix="/coding", tags=["coding"])
v1_router.include_router(codes_router, prefix="/codes", tags=["codes"])
v1_router.include_router(patients_router, prefix="/patients", tags=["patients"])
v1_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
v1_router.include_router(exports_router, prefix="/exports", tags=["exports"])
v1_router.include_router(admin_router, prefix="/admin", tags=["admin"])
v1_router.include_router(standards_router, prefix="/standards", tags=["standards"])
