import os
import shutil
import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.models.intelligence import AuditLog, RuntimeConfiguration
from app.schemas.administration import AuditResponse, RuntimeConfigResponse

DEFAULT_RUNTIME_CONFIG = {
    "stream_speed_seconds": 2.0,
    "alert_thresholds": {"off_spec_probability": 0.65, "quality_score": 70},
    "forecast_horizon": 12,
    "history_window": 20,
    "confidence_threshold": 0.6,
    "feature_flags": {
        "forecasting": True,
        "interventions": True,
        "relationship_discovery": True,
    },
    "relationship_threshold": 0.1,
    "recommendation_limit": 5,
}


class RuntimeConfigService:
    def get(self, session: Session, settings: Settings) -> RuntimeConfigResponse:
        row = session.scalar(
            select(RuntimeConfiguration).where(RuntimeConfiguration.singleton_key == "active")
        )
        if row is None:
            values = {
                **DEFAULT_RUNTIME_CONFIG,
                "stream_speed_seconds": settings.stream_interval_seconds,
                "forecast_horizon": settings.forecast_horizon,
                "history_window": settings.forecast_history_window,
            }
            row = RuntimeConfiguration(singleton_key="active", values=values)
            session.add(row)
            session.commit()
            session.refresh(row)
        return RuntimeConfigResponse.model_validate(row.values)

    def update(self, session: Session, values: RuntimeConfigResponse) -> RuntimeConfigResponse:
        row = session.scalar(
            select(RuntimeConfiguration).where(RuntimeConfiguration.singleton_key == "active")
        )
        if row is None:
            row = RuntimeConfiguration(singleton_key="active", values=values.model_dump())
            session.add(row)
        else:
            row.values = values.model_dump()
        session.commit()
        return values


class AuditService:
    def record(
        self,
        session: Session,
        action: str,
        entity: str,
        entity_id: str | None = None,
        details: dict[str, Any] | None = None,
        actor: str = "system",
        request_id: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            timestamp=datetime.now(UTC),
            actor=actor,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=details or {},
            request_id=request_id,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    @staticmethod
    def response(row: AuditLog) -> AuditResponse:
        return AuditResponse(
            audit_id=row.id,
            timestamp=row.timestamp,
            actor=row.actor,
            action=row.action,
            entity=row.entity,
            entity_id=row.entity_id,
            details=row.details,
            request_id=row.request_id,
        )


class MetricsService:
    def __init__(self) -> None:
        self.started = time.monotonic()
        self._lock = threading.RLock()
        self.request_count = 0
        self.response_count = 0
        self.error_count = 0
        self.throughput: dict[str, int] = defaultdict(int)
        self.latencies: dict[str, deque[dict[str, float]]] = defaultdict(lambda: deque(maxlen=500))

    def observe(self, category: str, latency_seconds: float, error: bool = False) -> None:
        with self._lock:
            self.latencies[category].append(
                {"timestamp": time.time(), "milliseconds": latency_seconds * 1000}
            )
            self.throughput[category] += 1

    def request_started(self) -> None:
        with self._lock:
            self.request_count += 1

    def response_finished(self, error: bool) -> None:
        with self._lock:
            self.response_count += 1
            if error:
                self.error_count += 1

    def snapshot(self, active_websockets: int = 0, stream_samples: int = 0) -> dict[str, Any]:
        process = psutil.Process(os.getpid())
        disk = shutil.disk_usage(Path.cwd())
        with self._lock:
            latency = {
                name: {
                    "count": len(rows),
                    "average_ms": (
                        sum(item["milliseconds"] for item in rows) / len(rows) if rows else 0
                    ),
                    "latest_ms": rows[-1]["milliseconds"] if rows else 0,
                    "trend": list(rows),
                }
                for name, rows in self.latencies.items()
            }
            return {
                "uptime_seconds": time.monotonic() - self.started,
                "request_count": self.request_count,
                "response_count": self.response_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(self.response_count, 1),
                "latency": latency,
                "throughput": {
                    **self.throughput,
                    "stream_samples": stream_samples,
                },
                "active_websocket_connections": active_websockets,
                "cpu_percent": process.cpu_percent(interval=None),
                "memory_bytes": process.memory_info().rss,
                "memory_percent": process.memory_percent(),
                "disk_total_bytes": disk.total,
                "disk_used_bytes": disk.used,
                "disk_free_bytes": disk.free,
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def database_probe(self, session: Session) -> tuple[bool, float]:
        started = time.perf_counter()
        try:
            session.execute(text("SELECT 1"))
            healthy = True
        except Exception:
            healthy = False
        latency = time.perf_counter() - started
        self.observe("database", latency, not healthy)
        return healthy, latency * 1000


metrics_service = MetricsService()
