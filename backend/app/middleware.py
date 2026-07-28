import time
from collections import defaultdict, deque
from threading import RLock
from uuid import uuid4

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.database.session import SessionFactory
from app.services.operations import AuditService, metrics_service

logger = get_logger(__name__)


class ProductionMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        max_payload_bytes: int = 2_000_000,
        rate_limit_per_minute: int = 300,
    ) -> None:
        super().__init__(app)
        self.max_payload_bytes = max_payload_bytes
        self.rate_limit = rate_limit_per_minute
        self.clients: dict[str, deque[float]] = defaultdict(deque)
        self._rate_lock = RLock()

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        try:
            content_length = int(request.headers.get("content-length", "0") or 0)
        except ValueError:
            return self._secured(
                JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid Content-Length header."},
                ),
                request_id,
            )
        if content_length > self.max_payload_bytes:
            return self._secured(
                JSONResponse(status_code=413, content={"detail": "Payload too large."}),
                request_id,
            )
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._rate_lock:
            recent = self.clients[client]
            while recent and recent[0] < now - 60:
                recent.popleft()
            if len(recent) >= self.rate_limit:
                return self._secured(
                    JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded."},
                    ),
                    request_id,
                )
            recent.append(now)
            if len(self.clients) > 10_000:
                self.clients = defaultdict(
                    deque,
                    {
                        key: values
                        for key, values in self.clients.items()
                        if values and values[-1] >= now - 60
                    },
                )
        started = time.perf_counter()
        metrics_service.request_started()
        try:
            response = await call_next(request)
        except Exception:
            metrics_service.response_finished(True)
            raise
        elapsed = time.perf_counter() - started
        metrics_service.response_finished(response.status_code >= 400)
        category = self._category(request.url.path)
        metrics_service.observe(category, elapsed, response.status_code >= 500)
        if request.method in {"POST", "PUT"} and category in {
            "prediction",
            "forecast",
            "recommendation",
            "simulation",
        }:
            try:
                with SessionFactory() as session:
                    await run_in_threadpool(
                        AuditService().record,
                        session,
                        self._audit_action(request.url.path, category),
                        category,
                        None,
                        {"path": request.url.path, "status": response.status_code},
                        request.headers.get("X-Actor", "operator"),
                        request_id,
                    )
            except Exception:
                # Audit persistence must not replace a successful API response.
                logger.exception("best_effort_audit_failed")
        logger.info(
            "endpoint_end",
            extra={
                "method": request.method,
                "path": request.url.path,
                "elapsed_ms": round(elapsed * 1000, 2),
                "slow": elapsed > 2,
            },
        )
        return self._secured(response, request_id)

    @staticmethod
    def _audit_action(path: str, category: str) -> str:
        if path == "/predict":
            return "prediction_request"
        if path == "/forecast":
            return "forecast_request"
        if path == "/forecast/simulate":
            return "simulation_request"
        if path == "/interventions/recommendations":
            return "recommendation_generation"
        if path.endswith("/decisions"):
            return "recommendation_decision"
        if path.endswith("/outcome"):
            return "recommendation_outcome"
        return f"{category}_change"

    @staticmethod
    def _category(path: str) -> str:
        if path.startswith("/predict"):
            return "prediction"
        if "simulate" in path:
            return "simulation"
        if path.startswith("/forecast"):
            return "forecast"
        if "recommend" in path:
            return "recommendation"
        if path.startswith("/admin") or path.startswith("/models"):
            return "admin"
        return "http"

    @staticmethod
    def _secured(response, request_id: str):
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
