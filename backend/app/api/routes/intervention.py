from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import DatabaseSession
from app.config.settings import get_settings
from app.models.intelligence import (
    ForecastHistory,
    ForecastRecommendation,
    RecommendationDecision,
    RecommendationOutcome,
)
from app.schemas.intervention import (
    EffectivenessResponse,
    ForecastRecommendationResponse,
    OutcomeEvaluationRequest,
    RecommendationDecisionCreate,
    RecommendationDecisionResponse,
    RecommendationGenerationRequest,
    RecommendationOutcomeResponse,
)
from app.services.forecasting.service import ForecastingService
from app.services.intervention import (
    InterventionEngine,
    OutcomeEvaluator,
    recommendation_response,
)
from app.services.streaming import get_streaming_service

router = APIRouter(tags=["forecast interventions"])


@router.post(
    "/interventions/recommendations",
    response_model=list[ForecastRecommendationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_recommendations(
    payload: RecommendationGenerationRequest, session: DatabaseSession
) -> list[ForecastRecommendationResponse]:
    forecast = session.get(ForecastHistory, payload.forecast_id)
    if forecast is None:
        raise HTTPException(status_code=404, detail="Forecast not found.")
    rows = InterventionEngine(ForecastingService(get_settings())).generate(
        session, forecast, payload.max_results, payload.max_variables
    )
    responses = [recommendation_response(row) for row in rows]
    for response in responses:
        await get_streaming_service().connections.broadcast("recommendation_created", response)
    return responses


@router.get(
    "/interventions/recommendations",
    response_model=list[ForecastRecommendationResponse],
)
def recommendation_history(
    session: DatabaseSession,
    state: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ForecastRecommendationResponse]:
    now = datetime.now(UTC)
    expired = session.scalars(
        select(ForecastRecommendation).where(
            ForecastRecommendation.state.in_(["proposed", "delayed"]),
            ForecastRecommendation.expires_at < now,
        )
    )
    for row in expired:
        row.state = "expired"
    session.commit()
    statement = select(ForecastRecommendation).order_by(ForecastRecommendation.created_at.desc())
    if state:
        statement = statement.where(ForecastRecommendation.state == state)
    return [recommendation_response(row) for row in session.scalars(statement.limit(limit))]


@router.get(
    "/interventions/recommendations/{recommendation_id}",
    response_model=ForecastRecommendationResponse,
)
def get_recommendation(
    recommendation_id: UUID, session: DatabaseSession
) -> ForecastRecommendationResponse:
    row = session.get(ForecastRecommendation, recommendation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    return recommendation_response(row)


@router.post(
    "/interventions/recommendations/{recommendation_id}/decisions",
    response_model=RecommendationDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def decide(
    recommendation_id: UUID,
    payload: RecommendationDecisionCreate,
    session: DatabaseSession,
) -> RecommendationDecisionResponse:
    row = session.get(ForecastRecommendation, recommendation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if row.state in {"expired", "evaluated"}:
        raise HTTPException(status_code=409, detail=f"Recommendation is {row.state}.")
    if payload.operator_action == "modified" and not payload.modified_values:
        raise HTTPException(status_code=422, detail="Modified values are required.")
    if payload.operator_action == "delayed" and not payload.delay_duration_seconds:
        raise HTTPException(status_code=422, detail="Delay duration is required.")
    decision = RecommendationDecision(
        recommendation_id=row.id,
        operator_action=payload.operator_action,
        reason=payload.reason,
        modified_values=payload.modified_values,
        delay_duration_seconds=payload.delay_duration_seconds,
        notes=payload.notes,
    )
    row.state = payload.operator_action
    if payload.operator_action == "delayed":
        row.expires_at = datetime.now(UTC) + timedelta(seconds=payload.delay_duration_seconds or 0)
    session.add(decision)
    session.commit()
    session.refresh(decision)
    session.refresh(row)
    response = RecommendationDecisionResponse(
        decision_id=decision.id,
        recommendation_id=row.id,
        timestamp=decision.created_at,
        state=row.state,
        **payload.model_dump(),
    )
    manager = get_streaming_service().connections
    await manager.broadcast("recommendation_decision", response)
    await manager.broadcast("recommendation_updated", recommendation_response(row))
    return response


@router.post(
    "/interventions/recommendations/{recommendation_id}/outcome",
    response_model=RecommendationOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_outcome(
    recommendation_id: UUID,
    payload: OutcomeEvaluationRequest,
    session: DatabaseSession,
) -> RecommendationOutcomeResponse:
    row = session.get(ForecastRecommendation, recommendation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if session.scalar(
        select(RecommendationOutcome).where(
            RecommendationOutcome.recommendation_id == recommendation_id
        )
    ):
        raise HTTPException(status_code=409, detail="Outcome already evaluated.")
    metrics = OutcomeEvaluator().evaluate(row, payload.observations)
    outcome = RecommendationOutcome(
        recommendation_id=row.id,
        observations=[point.model_dump(mode="json") for point in payload.observations],
        metrics=metrics,
    )
    row.state = "evaluated"
    session.add(outcome)
    session.commit()
    session.refresh(outcome)
    response = RecommendationOutcomeResponse(
        outcome_id=outcome.id,
        recommendation_id=row.id,
        metrics=metrics,
        evaluated_at=outcome.created_at,
    )
    await get_streaming_service().connections.broadcast("recommendation_outcome", response)
    return response


@router.get("/interventions/effectiveness", response_model=EffectivenessResponse)
def effectiveness(session: DatabaseSession) -> EffectivenessResponse:
    return OutcomeEvaluator().effectiveness(session)
