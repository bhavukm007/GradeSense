from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelRegister(AdminModel):
    version: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    model_kind: Literal["prediction", "forecast"]
    algorithm: str
    trained_at: datetime
    dataset_checksum: str
    feature_schema_checksum: str
    artifact_checksum: str
    artifact_path: str
    metrics: dict[str, Any]
    training_parameters: dict[str, Any]
    description: str
    status: Literal["active", "archived", "experimental"] = "experimental"


class RegisteredModelResponse(ModelRegister):
    model_id: UUID
    created_at: datetime


class ModelAction(AdminModel):
    model_id: UUID


class RuntimeConfigResponse(AdminModel):
    stream_speed_seconds: float = Field(ge=0.05, le=60)
    alert_thresholds: dict[str, float]
    forecast_horizon: int = Field(ge=1, le=120)
    history_window: int = Field(ge=5, le=120)
    confidence_threshold: float = Field(ge=0, le=1)
    feature_flags: dict[str, bool]
    relationship_threshold: float = Field(ge=0, le=1)
    recommendation_limit: int = Field(ge=1, le=10)


class AuditResponse(AdminModel):
    audit_id: UUID
    timestamp: datetime
    actor: str
    action: str
    entity: str
    entity_id: str | None
    details: dict[str, Any]
    request_id: str | None


class ExportRequest(AdminModel):
    resource: Literal[
        "forecasts",
        "recommendations",
        "decisions",
        "outcomes",
        "alerts",
        "feedback",
        "metrics",
        "models",
        "audit",
    ]
    format: Literal["json", "csv"]


class ExportDescriptor(AdminModel):
    resource: str
    formats: list[str]
    row_count: int | None = None
