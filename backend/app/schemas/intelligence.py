from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntelligenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProcessInput(IntelligenceModel):
    current_grade: str = Field(min_length=1, max_length=32)
    target_grade: str = Field(min_length=1, max_length=32)
    machine_speed: float = Field(ge=350, le=1_200)
    steam_pressure: float = Field(ge=3.0, le=9.5)
    dryer_temperature: float = Field(ge=80, le=145)
    moisture: float = Field(ge=2.5, le=10)
    basis_weight: float = Field(ge=40, le=220)
    caliper: float = Field(ge=45, le=300)
    pulp_consistency: float = Field(ge=2.2, le=5.5)
    stock_flow: float = Field(ge=1_200, le=5_500)
    refining_energy: float = Field(ge=80, le=260)
    headbox_pressure: float = Field(ge=1.5, le=5.5)
    reel_tension: float = Field(ge=1.0, le=6.5)
    ambient_temperature: float = Field(ge=12, le=42)
    humidity: float = Field(ge=20, le=95)


class FeatureContribution(IntelligenceModel):
    feature: str
    value: str | float
    contribution: float
    importance: float = Field(ge=0, le=1)
    direction: str


class Explanation(IntelligenceModel):
    summary: str
    top_contributing_features: list[FeatureContribution]
    feature_importance: dict[str, float]


class PredictionResponse(IntelligenceModel):
    prediction_id: UUID
    quality_score: float = Field(ge=0, le=100)
    off_spec_probability: float = Field(ge=0, le=1)
    expected_stabilization_time: float = Field(ge=0)
    model_version: str
    explanation: Explanation
    created_at: datetime


class Recommendation(IntelligenceModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    expected_improvement: float = Field(ge=0)
    affected_variables: list[str]


class RecommendationResponse(IntelligenceModel):
    recommendation_id: UUID
    prediction: PredictionResponse
    recommendations: list[Recommendation]
    created_at: datetime


class CorrelationPair(IntelligenceModel):
    first_variable: str
    second_variable: str
    correlation: float = Field(ge=-1, le=1)


class CorrelationResponse(IntelligenceModel):
    record_count: int
    correlation_matrix: dict[str, dict[str, float]]
    strongest_positive_correlations: list[CorrelationPair]
    strongest_negative_correlations: list[CorrelationPair]


class DatasetStatisticsResponse(IntelligenceModel):
    record_count: int
    generated_at: datetime
    columns: list[str]
    missing_values: dict[str, int]
    numeric_summary: dict[str, dict[str, float]]
    grade_distribution: dict[str, int]


class DatasetRegenerateRequest(IntelligenceModel):
    records: int = Field(default=20_000, ge=20_000, le=250_000)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class DatasetRegenerateResponse(IntelligenceModel):
    records: int
    dataset_path: str
    model_version: str
    training_metrics: dict[str, float]


class ModelInfoResponse(IntelligenceModel):
    model_type: str
    model_version: str
    trained_at: datetime
    training_records: int
    feature_count: int
    target_metrics: dict[str, float]
    dataset_checksum: str
    supported_outputs: list[str]
    artifact_path: str


class PaginationMeta(IntelligenceModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PredictionHistoryItem(IntelligenceModel):
    prediction_id: UUID
    model_version: str
    input_data: ProcessInput
    quality_score: float
    off_spec_probability: float
    expected_stabilization_time: float
    explanation: Explanation
    created_at: datetime


class PredictionHistoryResponse(IntelligenceModel):
    items: list[PredictionHistoryItem]
    pagination: PaginationMeta


class RecommendationHistoryItem(IntelligenceModel):
    recommendation_id: UUID
    prediction_id: UUID
    recommendations: list[Recommendation]
    created_at: datetime


class RecommendationHistoryResponse(IntelligenceModel):
    items: list[RecommendationHistoryItem]
    pagination: PaginationMeta
