"""Custom application exceptions with HTTP status code mapping."""

from __future__ import annotations


class AutoCodeException(Exception):
    """Base exception for the Auto Code application."""

    status_code: int = 500
    detail: str = "An internal error occurred."

    def __init__(self, detail: str | None = None, *, status_code: int | None = None) -> None:
        self.detail = detail or self.__class__.detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(AutoCodeException):
    """Resource not found."""

    status_code = 404
    detail = "The requested resource was not found."


class UnauthorizedError(AutoCodeException):
    """Authentication required or invalid credentials."""

    status_code = 401
    detail = "Authentication credentials are missing or invalid."


class ForbiddenError(AutoCodeException):
    """Insufficient permissions."""

    status_code = 403
    detail = "You do not have permission to perform this action."


class ValidationError(AutoCodeException):
    """Request validation failure beyond pydantic defaults."""

    status_code = 422
    detail = "The request data is invalid."


class RateLimitError(AutoCodeException):
    """Rate limit exceeded."""

    status_code = 429
    detail = "Rate limit exceeded. Please try again later."


class ExternalServiceError(AutoCodeException):
    """Failure communicating with an external service (LLM, Qdrant, etc.)."""

    status_code = 502
    detail = "An external service is temporarily unavailable."
