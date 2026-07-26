from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.dependencies import DatabaseSession
from app.config.settings import get_settings
from app.models.intelligence import (
    ForecastCrossingEvent,
    ForecastHistory,
    InterventionSimulation,
)
from app.schemas.forecasting import (
    ForecastHistoryResponse,
    ForecastRequest,
    ForecastResponse,
    ForecastSimulationRequest,
    ForecastSimulationResponse,
)
from app.services.constraints import ConstraintEngine
from app.services.forecasting.relationships import SequentialRelationshipService
from app.services.forecasting.service import ForecastingService

router = APIRouter(tags=["basis-weight forecasting"])


@lru_cache(maxsize=2)
def _sequential_dataset(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns  # The timestamp is part of the cache key.
    return pd.read_csv(path)


@lru_cache(maxsize=64)
def _relationship_result(
    path: str,
    modified_ns: int,
    max_lag: int,
    grade_pair: str | None,
    stage: str | None,
    method: str | None,
    min_strength: float,
    limit: int,
) -> dict:
    return SequentialRelationshipService().discover(
        _sequential_dataset(path, modified_ns),
        max_lag=max_lag,
        grade_pair=grade_pair,
        stage=stage,
        method=method,
        min_strength=min_strength,
        limit=limit,
    )


def response_from_row(row: ForecastHistory) -> ForecastResponse:
    return ForecastResponse(
        forecast_id=row.id,
        transition_id=row.transition_id,
        model_version=row.model_version,
        history_window=len(row.request_data["history"]),
        forecast_horizon=len(row.trajectory),
        confidence=row.confidence,
        trajectory=row.trajectory,
        specification=row.specification,
        top_influencing_variables=[
            (str(item[0]), float(item[1])) for item in row.top_influencing_variables
        ],
        explanation=row.explanation,
        created_at=row.created_at,
    )


@router.post("/forecast", response_model=ForecastResponse)
def create_forecast(request: ForecastRequest, session: DatabaseSession) -> ForecastResponse:
    service = ForecastingService(get_settings())
    try:
        result = service.forecast(request)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    row = ForecastHistory(
        id=result.forecast_id,
        transition_id=result.transition_id,
        model_version=result.model_version,
        request_data=request.model_dump(mode="json"),
        trajectory=[point.model_dump(mode="json") for point in result.trajectory],
        specification=result.specification.model_dump(mode="json"),
        confidence=result.confidence,
        explanation=result.explanation,
        top_influencing_variables=[list(item) for item in result.top_influencing_variables],
    )
    session.add(row)
    crossing = result.specification
    if crossing.predicted_crossing_step and crossing.predicted_crossing_time:
        point = result.trajectory[crossing.predicted_crossing_step - 1]
        session.add(
            ForecastCrossingEvent(
                forecast_id=row.id,
                crossing_step=crossing.predicted_crossing_step,
                crossing_time=crossing.predicted_crossing_time,
                direction=("high" if point.basis_weight > crossing.target_basis_weight else "low"),
                probability=crossing.crossing_probability,
            )
        )
    session.commit()
    session.refresh(row)
    return response_from_row(row)


@router.get("/forecast/history", response_model=ForecastHistoryResponse)
def forecast_history(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ForecastHistoryResponse:
    rows = session.scalars(
        select(ForecastHistory).order_by(ForecastHistory.created_at.desc()).limit(limit)
    ).all()
    total = session.scalar(select(func.count(ForecastHistory.id))) or 0
    return ForecastHistoryResponse(items=[response_from_row(row) for row in rows], total=total)


@router.get("/forecast/{forecast_id}", response_model=ForecastResponse)
def get_forecast(forecast_id: UUID, session: DatabaseSession) -> ForecastResponse:
    row = session.get(ForecastHistory, forecast_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Forecast not found.")
    return response_from_row(row)


@router.post(
    "/forecast/simulate",
    response_model=ForecastSimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
def simulate_forecast(
    payload: ForecastSimulationRequest, session: DatabaseSession
) -> ForecastSimulationResponse:
    row = session.get(ForecastHistory, payload.forecast_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Forecast not found.")
    request = ForecastRequest.model_validate(row.request_data)
    validation = ConstraintEngine().validate(request, payload.changes)
    if not validation.feasible:
        raise HTTPException(
            status_code=422,
            detail={"message": "Unsafe intervention.", "validation": validation.model_dump()},
        )
    baseline = response_from_row(row)
    result = ForecastingService(get_settings()).simulate(request, baseline, payload.changes)
    session.add(
        InterventionSimulation(
            id=result.simulation_id,
            forecast_id=result.forecast_id,
            recommendation_id=result.recommendation_id,
            changes=[change.model_dump(mode="json") for change in result.changes],
            baseline_trajectory=[
                point.model_dump(mode="json") for point in result.baseline_trajectory
            ],
            intervention_trajectory=[
                point.model_dump(mode="json") for point in result.intervention_trajectory
            ],
            metrics={
                "baseline_crossing_probability": result.baseline_crossing_probability,
                "intervention_crossing_probability": result.intervention_crossing_probability,
                "risk_reduction": result.risk_reduction,
                "expected_deviation_reduction": result.expected_deviation_reduction,
                "expected_stabilization_improvement": result.expected_stabilization_improvement,
                "crossing_delay_steps": result.crossing_delay_steps,
                "crossing_avoided": result.crossing_avoided,
                "confidence": result.confidence,
            },
            explanation=result.explanation,
        )
    )
    session.commit()
    return result


@router.get("/relationships/discovery")
def relationship_discovery(
    max_lag: Annotated[int, Query(ge=1, le=60)] = 12,
    grade_pair: str | None = None,
    stage: Annotated[str | None, Query(pattern="^(early|middle|late)$")] = None,
    method: Annotated[str | None, Query(pattern="^(lag|nonlinear|interaction)$")] = None,
    min_strength: Annotated[float, Query(ge=0, le=1)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> dict:
    settings = get_settings()
    path = Path(settings.sequential_dataset_path).resolve()
    if not path.exists():
        raise HTTPException(status_code=503, detail="Sequential dataset is not available.")
    return _relationship_result(
        str(path),
        path.stat().st_mtime_ns,
        max_lag=max_lag,
        grade_pair=grade_pair,
        stage=stage,
        method=method,
        min_strength=min_strength,
        limit=limit,
    )
