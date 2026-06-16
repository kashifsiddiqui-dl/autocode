"""FastAPI dependency injection — re-exports from core.dependencies.

This module provides a convenience import path for the most commonly used
dependencies.  The canonical implementations live in ``app.core.dependencies``.
"""

from __future__ import annotations

from app.core.dependencies import (
    AdminUser,
    AuthUser,
    CurrentUser,
    DBSession,
    get_current_user,
    get_db,
    get_qdrant_client,
    require_role,
)

__all__ = [
    "AdminUser",
    "AuthUser",
    "CurrentUser",
    "DBSession",
    "get_current_user",
    "get_db",
    "get_qdrant_client",
    "require_role",
]
