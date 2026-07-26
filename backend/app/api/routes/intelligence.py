from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import DatabaseSession
from app.config.settings import get_settings
from app.schemas.intelligence import (
    CorrelationResponse,
    DatasetRegenerateRequest,
    DatasetRegenerateResponse,
    DatasetStatisticsResponse,
    ModelInfoResponse,
    PredictionHistoryResponse,
    PredictionResponse,
    ProcessInput,
    RecommendationHistoryResponse,
    RecommendationResponse,
)
from app.services.intelligence import IntelligenceService

router = APIRouter(tags=["intelligence"])


def get_intelligence_service(session: DatabaseSession) -> IntelligenceService:
    return IntelligenceService(get_settings(), session)


IntelligenceDependency = Annotated[IntelligenceService, Depends(get_intelligence_service)]


@router.post("/predict", response_model=PredictionResponse, summary="Predict transition quality")
def predict(process_input: ProcessInput, service: IntelligenceDependency) -> PredictionResponse:
    return service.predict(process_input)


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Generate model-evaluated corrective actions",
)
def recommend(
    process_input: ProcessInput, service: IntelligenceDependency
) -> RecommendationResponse:
    return service.recommend(process_input)


@router.get(
    "/correlations",
    response_model=CorrelationResponse,
    summary="Discover process correlations",
)
def correlations(
    service: IntelligenceDependency,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> CorrelationResponse:
    return service.correlations(limit)


@router.get(
    "/dataset/statistics",
    response_model=DatasetStatisticsResponse,
    summary="Describe the generated industrial dataset",
)
def dataset_statistics(
    service: IntelligenceDependency,
) -> DatasetStatisticsResponse:
    return service.dataset_statistics()


@router.post(
    "/dataset/regenerate",
    response_model=DatasetRegenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate the dataset and retrain the model",
)
def regenerate_dataset(
    request: DatasetRegenerateRequest,
    service: IntelligenceDependency,
) -> DatasetRegenerateResponse:
    return service.regenerate(request.records, request.seed)


@router.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Describe the active trained model",
)
def model_info(service: IntelligenceDependency) -> ModelInfoResponse:
    return service.model_info()


@router.get(
    "/history/predictions",
    response_model=PredictionHistoryResponse,
    summary="List persisted predictions",
)
def prediction_history(
    service: IntelligenceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PredictionHistoryResponse:
    return service.prediction_history(page, page_size)


@router.get(
    "/history/recommendations",
    response_model=RecommendationHistoryResponse,
    summary="List persisted recommendations",
)
def recommendation_history(
    service: IntelligenceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RecommendationHistoryResponse:
    return service.recommendation_history(page, page_size)
