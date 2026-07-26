from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exception: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exception.status_code,
            content=error_payload("http_error", str(exception.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exception: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "validation_error",
                "Request validation failed.",
                exception.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exception: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={
                "path": request.url.path,
                "exception_type": type(exception).__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_server_error", "An unexpected error occurred."),
        )
