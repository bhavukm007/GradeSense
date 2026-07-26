from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.forecasting import InterventionChange, TrajectoryPoint

RecommendationState = Literal[
    "proposed",
    "accepted",
    "rejected",
    "modified",
    "delayed",
    "expired",
    "applied",
    "evaluated",
]
DecisionAction = Literal["accepted", "rejected", "modified", "delayed", "applied"]


class InterventionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConstraintValidation(InterventionModel):
    feasible: bool
    checks: list[str]
    violations: list[str]


class RecommendationMetrics(InterventionModel):
    crossing_probability_before: float
    crossing_probability_after: float
    predicted_peak_deviation_before: float
    predicted_peak_deviation_after: float
    predicted_stabilization_time_before: int | None
    predicted_stabilization_time_after: int | None
    estimated_improvement: float
    crossing_avoided: bool
    crossing_delay_steps: int | None


class RecommendationExplanation(InterventionModel):
    selection_reason: str
    forecast_causes: list[str]
    trajectory_effect: str
    expected_risks: list[str]
    remaining_uncertainty: str


class ForecastRecommendationResponse(InterventionModel):
    recommendation_id: UUID
    forecast_id: UUID
    state: RecommendationState
    rank: int
    affected_variables: list[str]
    changes: list[InterventionChange]
    baseline_trajectory: list[TrajectoryPoint]
    intervention_trajectory: list[TrajectoryPoint]
    metrics: RecommendationMetrics
    confidence: float
    constraint_validation: ConstraintValidation
    explanation: RecommendationExplanation
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None


class RecommendationGenerationRequest(InterventionModel):
    forecast_id: UUID
    max_results: int = Field(default=5, ge=1, le=10)
    max_variables: int = Field(default=2, ge=1, le=3)


class RecommendationDecisionCreate(InterventionModel):
    operator_action: DecisionAction
    reason: str | None = None
    modified_values: dict[str, float] | None = None
    delay_duration_seconds: int | None = Field(default=None, ge=1, le=86400)
    notes: str | None = None


class RecommendationDecisionResponse(RecommendationDecisionCreate):
    decision_id: UUID
    recommendation_id: UUID
    timestamp: datetime
    state: RecommendationState


class OutcomeEvaluationRequest(InterventionModel):
    observations: list[TrajectoryPoint] = Field(min_length=3)


class RecommendationOutcomeResponse(InterventionModel):
    outcome_id: UUID
    recommendation_id: UUID
    metrics: dict[str, float | bool]
    evaluated_at: datetime


class EffectivenessResponse(InterventionModel):
    evaluated_count: int
    crossing_avoidance_rate: float
    crossing_delay_rate: float
    mean_prediction_error: float
    mean_deviation_improvement: float
    mean_stabilization_improvement: float
