"""
Centralized Error Handling and Structured Error Responses for EpiSense API (Phase 12).
Provides machine-readable error bodies, stable error codes, and correlation tracking.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from episense.schemas.base import EpiSenseBaseModel
from episense.exceptions import EpiSenseError
from episense.logging import get_logger

logger = get_logger("api.errors")


class APIErrorDetail(EpiSenseBaseModel):
    """Machine-readable structured error representation."""
    code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None


class APIErrorResponse(EpiSenseBaseModel):
    """Top-level error payload returned to API clients."""
    error: APIErrorDetail


class APIError(Exception):
    """Base API exception with HTTP status code and stable error code."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class APIResourceNotFoundError(APIError):
    def __init__(self, resource_type: str, resource_id: Any, details: Optional[Any] = None):
        super().__init__(
            message=f"{resource_type} with identifier '{resource_id}' was not found.",
            code=f"{resource_type.upper()}_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class APIValidationError(APIError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class APIBadRequestError(APIError):
    def __init__(self, message: str, code: str = "BAD_REQUEST", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class APIDuplicateError(APIError):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="DUPLICATE_DOCUMENT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


def get_request_id(request: Request) -> Optional[str]:
    """Extracts request correlation ID from request state or headers."""
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    req_id = get_request_id(request)
    error_detail = APIErrorDetail(
        code=exc.code,
        message=exc.message,
        request_id=req_id,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_detail.model_dump()},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = get_request_id(request)
    code_map = {
        400: "BAD_REQUEST",
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    error_detail = APIErrorDetail(
        code=code,
        message=str(exc.detail),
        request_id=req_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_detail.model_dump()},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = get_request_id(request)
    # Sanitize pydantic validation errors
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        errors.append({"location": loc, "message": err.get("msg"), "type": err.get("type")})

    error_detail = APIErrorDetail(
        code="VALIDATION_ERROR",
        message="Request validation failed. Check parameter types and required fields.",
        request_id=req_id,
        details=errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": error_detail.model_dump()},
    )


async def domain_exception_handler(request: Request, exc: EpiSenseError) -> JSONResponse:
    req_id = get_request_id(request)
    logger.warning("Domain exception caught at API boundary: %s", exc)
    error_detail = APIErrorDetail(
        code="EPISENSE_DOMAIN_ERROR",
        message=str(exc),
        request_id=req_id,
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": error_detail.model_dump()},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = get_request_id(request)
    logger.exception("Unhandled server exception: %s", exc)
    error_detail = APIErrorDetail(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred.",
        request_id=req_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": error_detail.model_dump()},
    )
