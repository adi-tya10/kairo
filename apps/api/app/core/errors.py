from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class KairoError(Exception):
    """Base exception class for all typed KAIRO errors."""
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class TenantIsolationError(KairoError):
    def __init__(self, message: str = "Tenant boundary violation detected", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code="TENANT_ISOLATION_VIOLATION",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class AccessRestrictedError(KairoError):
    def __init__(self, message: str = "Access Restricted: You are not authorized to view this repository", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code="ACCESS_RESTRICTED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class SignatureVerificationError(KairoError):
    def __init__(self, message: str = "Invalid webhook HMAC signature"):
        super().__init__(
            message=message,
            error_code="INVALID_SIGNATURE",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

class DatabaseError(KairoError):
    def __init__(self, message: str = "Database operation failed", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )

class DatabaseWriteError(DatabaseError):
    def __init__(self, message: str = "Failed to persist record to database", details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            details=details,
        )
        self.error_code = "DATABASE_WRITE_ERROR"


async def kairo_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """RFC 7807 problem details handler for KairoError and derived exceptions."""
    if isinstance(exc, KairoError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"https://api.kairo.dev/errors/{exc.error_code.lower()}",
                "title": exc.error_code,
                "status": exc.status_code,
                "detail": exc.message,
                "instance": str(request.url),
                "details": exc.details,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "https://api.kairo.dev/errors/internal_error",
            "title": "INTERNAL_ERROR",
            "status": 500,
            "detail": str(exc),
            "instance": str(request.url),
            "details": {},
        },
    )
