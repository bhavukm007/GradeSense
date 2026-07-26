from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ModelMetadata(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_metadata"

    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    model_type: Mapped[str] = mapped_column(String(128), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    training_records: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)


class PredictionHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prediction_history"

    model_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    off_spec_probability: Mapped[float] = mapped_column(Float, nullable=False)
    stabilization_time: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class RecommendationHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_history"

    prediction_id: Mapped[UUID] = mapped_column(
        ForeignKey("prediction_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)


class AlertHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alert_history"

    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_variables: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prediction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prediction_history.id", ondelete="SET NULL"), index=True
    )


class OperatorFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "operator_feedback"

    prediction_id: Mapped[UUID] = mapped_column(
        ForeignKey("prediction_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class RollingMetricSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rolling_metric_snapshots"

    window: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class StreamingSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streaming_sessions"

    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ForecastHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "forecast_history"

    transition_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    request_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    trajectory: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    specification: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    top_influencing_variables: Mapped[list[list[Any]]] = mapped_column(JSON, nullable=False)


class ForecastCrossingEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "forecast_crossing_events"

    forecast_id: Mapped[UUID] = mapped_column(
        ForeignKey("forecast_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crossing_step: Mapped[int] = mapped_column(Integer, nullable=False)
    crossing_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)


class InterventionSimulation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intervention_simulations"

    forecast_id: Mapped[UUID] = mapped_column(
        ForeignKey("forecast_history.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True, index=True)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    baseline_trajectory: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    intervention_trajectory: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class ForecastRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "forecast_recommendations"

    forecast_id: Mapped[UUID] = mapped_column(
        ForeignKey("forecast_history.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    affected_variables: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    baseline_trajectory: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    intervention_trajectory: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    constraint_validation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class RecommendationDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_decisions"

    recommendation_id: Mapped[UUID] = mapped_column(
        ForeignKey("forecast_recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operator_action: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    modified_values: Mapped[dict[str, float] | None] = mapped_column(JSON)
    delay_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class RecommendationOutcome(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_outcomes"

    recommendation_id: Mapped[UUID] = mapped_column(
        ForeignKey("forecast_recommendations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    observations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class RegisteredModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "registered_models"

    version: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    model_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    algorithm: Mapped[str] = mapped_column(String(160), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_schema_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    training_parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    __table_args__ = (
        UniqueConstraint("model_kind", "version", name="uq_registered_models_kind_version"),
    )


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(160), nullable=False)
    action: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(96), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(96), index=True)


class RuntimeConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runtime_configuration"

    singleton_key: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, default="active"
    )
    values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
