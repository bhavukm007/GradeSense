from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.intelligence import PredictionResponse, ProcessInput, Recommendation


class RealtimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AlertResponse(RealtimeModel):
    id: UUID
    severity: Literal["info", "warning", "critical"]
    title: str
    description: str
    timestamp: datetime
    affected_variables: list[str]
    suggested_action: str
    acknowledged: bool
    acknowledged_at: datetime | None = None
    prediction_id: UUID | None = None


class FeedbackCreate(RealtimeModel):
    prediction_id: UUID
    outcome: Literal[
        "recommendation_accepted",
        "recommendation_ignored",
        "recommendation_ineffective",
        "problem_resolved",
    ]
    notes: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(FeedbackCreate):
    id: UUID
    created_at: datetime


class DriftResponse(RealtimeModel):
    score: float = Field(ge=0)
    severity: Literal["stable", "watch", "warning", "critical"]
    drifting_variables: dict[str, float]
    prediction_drift: float
    recommended_action: str
    calculated_at: datetime


class RollingWindow(RealtimeModel):
    window: str
    average_quality: float
    average_off_spec_probability: float
    average_stabilization_time: float
    recommendation_frequency: int
    alert_frequency: int
    prediction_count: int


class StreamStatusResponse(RealtimeModel):
    status: Literal["starting", "running", "stopped"]
    session_id: UUID | None
    started_at: datetime | None
    sample_count: int
    connected_clients: int
    latest_sample_at: datetime | None


class LiveMetricsResponse(RealtimeModel):
    sensor: ProcessInput | None
    prediction: PredictionResponse | None
    recommendations: list[Recommendation]
    alerts: list[AlertResponse]
    drift: DriftResponse | None
    updated_at: datetime | None


class WebSocketEvent(RealtimeModel):
    event: Literal[
        "prediction",
        "recommendation",
        "sensor_update",
        "alert",
        "drift",
        "system_status",
        "heartbeat",
    ]
    timestamp: datetime
    data: dict
