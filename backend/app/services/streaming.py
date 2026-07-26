import asyncio
import time
from collections import deque
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pandas as pd
from fastapi import WebSocket

from app.config.settings import Settings
from app.database.session import SessionFactory
from app.models.intelligence import RollingMetricSnapshot, StreamingSession
from app.schemas.forecasting import ForecastRequest, SequencePoint
from app.schemas.intelligence import ProcessInput
from app.schemas.realtime import (
    LiveMetricsResponse,
    RollingWindow,
    StreamStatusResponse,
)
from app.services.alert import AlertService
from app.services.drift import DriftService
from app.services.forecasting.service import ForecastingService
from app.services.intelligence import IntelligenceService
from app.services.operations import AuditService, metrics_service


class ConnectionManager:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.clients.discard(websocket)

    async def broadcast(self, event: str, data: Any) -> None:
        payload = {
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": (data.model_dump(mode="json") if hasattr(data, "model_dump") else data),
        }
        stale: list[WebSocket] = []
        for client in tuple(self.clients):
            send_started = time.perf_counter()
            try:
                await client.send_json(payload)
                metrics_service.observe("websocket", time.perf_counter() - send_started)
            except Exception:
                metrics_service.observe("websocket", time.perf_counter() - send_started, True)
                stale.append(client)
        for client in stale:
            self.disconnect(client)


class StreamingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.connections = ConnectionManager()
        self.status = "stopped"
        self.session_id: UUID | None = None
        self.started_at: datetime | None = None
        self.sample_count = 0
        self.latest_sample_at: datetime | None = None
        self.latest = LiveMetricsResponse(
            sensor=None,
            prediction=None,
            recommendations=[],
            alerts=[],
            drift=None,
            updated_at=None,
        )
        self._task: asyncio.Task[None] | None = None
        self._history: deque[dict[str, Any]] = deque(maxlen=720)
        self._recent_samples: deque[ProcessInput] = deque(maxlen=120)
        self._sequence_history: deque[dict[str, Any]] = deque(
            maxlen=settings.forecast_history_window
        )
        self._prediction_risks: deque[float] = deque(maxlen=120)
        self._training: pd.DataFrame | None = None
        self._cursor = 0

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        source = (
            self.settings.sequential_dataset_path
            if self.settings.sequential_dataset_path.exists()
            else self.settings.dataset_path
        )
        self._training = pd.read_csv(source)
        self.status = "starting"
        self.started_at = datetime.now(UTC)
        with SessionFactory() as session:
            row = StreamingSession(status="running", started_at=self.started_at, sample_count=0)
            session.add(row)
            session.commit()
            session.refresh(row)
            self.session_id = row.id
            AuditService().record(session, "stream_start", "streaming_session", str(row.id))
        self.status = "running"
        self._task = asyncio.create_task(self._run(), name="gradesense-process-stream")

    async def stop(self) -> None:
        self.status = "stopped"
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        if self.session_id:
            with SessionFactory() as session:
                row = session.get(StreamingSession, self.session_id)
                if row:
                    row.status = "stopped"
                    row.stopped_at = datetime.now(UTC)
                    row.sample_count = self.sample_count
                    session.commit()
                AuditService().record(
                    session,
                    "stream_stop",
                    "streaming_session",
                    str(self.session_id),
                    {"sample_count": self.sample_count},
                )
        await self.connections.broadcast("system_status", self.status_response())

    async def _run(self) -> None:
        await self.connections.broadcast("system_status", self.status_response())
        while True:
            try:
                await self.process_next_sample()
                await self.connections.broadcast(
                    "heartbeat",
                    {"status": self.status, "sample_count": self.sample_count},
                )
            except Exception:
                # A malformed sample must not terminate the long-running worker.
                await asyncio.sleep(1)
            await asyncio.sleep(self.settings.stream_interval_seconds)

    async def process_next_sample(self) -> LiveMetricsResponse:
        process_started = time.perf_counter()
        assert self._training is not None
        row = self._training.iloc[self._cursor % len(self._training)]
        self._cursor += 1
        sample = ProcessInput.model_validate(
            {field: row[field] for field in ProcessInput.model_fields}
        )
        if "transition_id" in row.index:
            transition_id = str(row["transition_id"])
            if (
                self._sequence_history
                and self._sequence_history[-1]["transition_id"] != transition_id
            ):
                self._sequence_history.clear()
            self._sequence_history.append(row.to_dict())
        with SessionFactory() as session:
            intelligence = IntelligenceService(self.settings, session)
            result = intelligence.recommend(sample)
            alerts = AlertService().evaluate(session, sample, result.prediction, self.latest.sensor)
        self.sample_count += 1
        now = datetime.now(UTC)
        self.latest_sample_at = now
        self._recent_samples.append(sample)
        self._prediction_risks.append(result.prediction.off_spec_probability)
        drift = DriftService().calculate(
            list(self._recent_samples), self._training, list(self._prediction_risks)
        )
        self._history.append(
            {
                "timestamp": now,
                "quality": result.prediction.quality_score,
                "risk": result.prediction.off_spec_probability,
                "stabilization": result.prediction.expected_stabilization_time,
                "recommendations": len(result.recommendations),
                "alerts": len(alerts),
            }
        )
        self.latest = LiveMetricsResponse(
            sensor=sample,
            prediction=result.prediction,
            recommendations=result.recommendations,
            alerts=alerts,
            drift=drift,
            updated_at=now,
        )
        await self.connections.broadcast("sensor_update", sample)
        await self.connections.broadcast("prediction", result.prediction)
        await self.connections.broadcast(
            "recommendation",
            {"recommendations": [item.model_dump(mode="json") for item in result.recommendations]},
        )
        for alert in alerts:
            await self.connections.broadcast("alert", alert)
        await self.connections.broadcast("drift", drift)
        if (
            len(self._sequence_history) == self.settings.forecast_history_window
            and self.settings.forecast_model_path.exists()
        ):
            sequence = list(self._sequence_history)
            forecast_request = ForecastRequest(
                transition_id=str(sequence[-1]["transition_id"]),
                current_grade=str(sequence[-1]["current_grade"]),
                target_grade=str(sequence[-1]["target_grade"]),
                target_basis_weight=float(sequence[-1]["target_basis_weight"]),
                history=[
                    SequencePoint.model_validate(
                        {field: item[field] for field in SequencePoint.model_fields}
                    )
                    for item in sequence
                ],
            )
            forecast = ForecastingService(self.settings).forecast(forecast_request)
            await self.connections.broadcast("basis_forecast", forecast)
        if self.sample_count % 10 == 0:
            self._persist_snapshot()
        metrics_service.observe("stream", time.perf_counter() - process_started)
        return self.latest

    def rolling(self) -> list[RollingWindow]:
        now = datetime.now(UTC)
        return [
            self._window("1 minute", now - timedelta(minutes=1)),
            self._window("10 minutes", now - timedelta(minutes=10)),
            self._window("1 hour", now - timedelta(hours=1)),
        ]

    def _window(self, name: str, cutoff: datetime) -> RollingWindow:
        rows = [row for row in self._history if row["timestamp"] >= cutoff]
        count = len(rows)

        def average(key: str) -> float:
            return sum(row[key] for row in rows) / count if count else 0.0

        return RollingWindow(
            window=name,
            average_quality=round(average("quality"), 3),
            average_off_spec_probability=round(average("risk"), 5),
            average_stabilization_time=round(average("stabilization"), 3),
            recommendation_frequency=sum(row["recommendations"] for row in rows),
            alert_frequency=sum(row["alerts"] for row in rows),
            prediction_count=count,
        )

    def _persist_snapshot(self) -> None:
        with SessionFactory() as session:
            for window in self.rolling():
                session.add(
                    RollingMetricSnapshot(
                        window=window.window, metrics=window.model_dump(mode="json")
                    )
                )
            session.commit()

    def status_response(self) -> StreamStatusResponse:
        return StreamStatusResponse(
            status=self.status,
            session_id=self.session_id,
            started_at=self.started_at,
            sample_count=self.sample_count,
            connected_clients=len(self.connections.clients),
            latest_sample_at=self.latest_sample_at,
        )


streaming_service: StreamingService | None = None


def get_streaming_service(settings: Settings | None = None) -> StreamingService:
    global streaming_service
    if streaming_service is None:
        from app.config.settings import get_settings

        streaming_service = StreamingService(settings or get_settings())
    return streaming_service
