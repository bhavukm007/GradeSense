from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ForecastModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SequencePoint(ForecastModel):
    timestamp: datetime
    timestep: int = Field(ge=0)
    stock_flow: float
    filler_flow: float
    steam_pressure: float
    machine_speed: float
    dryer_temperature: float
    moisture: float
    ash: float
    caliper: float
    basis_weight: float
    reel_tension: float
    transition_progress: float = Field(ge=0, le=1)


class ForecastRequest(ForecastModel):
    transition_id: str = Field(min_length=1, max_length=64)
    current_grade: str
    target_grade: str
    target_basis_weight: float = Field(gt=0)
    history: list[SequencePoint]
    forecast_horizon: int | None = Field(default=None, ge=1, le=120)


class TrajectoryPoint(ForecastModel):
    step: int
    timestamp: datetime
    basis_weight: float
    lower_bound: float
    upper_bound: float
    deviation_pct: float
    lower_spec_limit: float
    upper_spec_limit: float


class SpecificationStatus(ForecastModel):
    target_basis_weight: float
    lower_spec_limit: float
    upper_spec_limit: float
    current_deviation_pct: float
    maximum_predicted_deviation_pct: float
    crossing_probability: float = Field(ge=0, le=1)
    predicted_crossing_step: int | None
    predicted_crossing_time: datetime | None
    remaining_safe_operating_seconds: float | None
    predicted_stabilization_step: int | None


class ForecastResponse(ForecastModel):
    forecast_id: UUID
    transition_id: str
    model_version: str
    history_window: int
    forecast_horizon: int
    confidence: float = Field(ge=0, le=1)
    trajectory: list[TrajectoryPoint]
    specification: SpecificationStatus
    top_influencing_variables: list[tuple[str, float]]
    explanation: str
    created_at: datetime


class InterventionChange(ForecastModel):
    variable: Literal[
        "stock_flow",
        "filler_flow",
        "steam_pressure",
        "machine_speed",
        "dryer_temperature",
        "reel_tension",
    ]
    value: float


class ForecastSimulationRequest(ForecastModel):
    forecast_id: UUID
    changes: list[InterventionChange] = Field(min_length=1, max_length=4)


class ForecastSimulationResponse(ForecastModel):
    simulation_id: UUID
    forecast_id: UUID
    recommendation_id: UUID
    changes: list[InterventionChange]
    baseline_trajectory: list[TrajectoryPoint]
    intervention_trajectory: list[TrajectoryPoint]
    baseline_crossing_probability: float
    intervention_crossing_probability: float
    risk_reduction: float
    expected_deviation_reduction: float
    expected_stabilization_improvement: int
    crossing_delay_steps: int | None
    crossing_avoided: bool
    confidence: float
    explanation: str
    created_at: datetime


class ForecastHistoryResponse(ForecastModel):
    items: list[ForecastResponse]
    total: int
