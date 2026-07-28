import asyncio
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID

import psutil
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import DatabaseSession
from app.config.settings import get_settings
from app.core.logging import get_logger
from app.database.session import SessionFactory
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
    RecommendationAuditEvent,
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
logger = get_logger(__name__)


def _endpoint_started(name: str) -> tuple[float, int]:
    try:
        memory = psutil.Process().memory_info().rss
    except Exception:
        logger.exception("recommendation_memory_probe_failed", extra={"endpoint": name})
        memory = -1
    logger.info("recommendation_endpoint_start", extra={"endpoint": name, "memory_before": memory})
    return perf_counter(), memory


def _endpoint_finished(name: str, started: float, memory_before: int, **details: object) -> None:
    try:
        memory_after = psutil.Process().memory_info().rss
    except Exception:
        logger.exception("recommendation_memory_probe_failed", extra={"endpoint": name})
        memory_after = -1
    logger.info(
        "recommendation_endpoint_end",
        extra={
            "endpoint": name,
            "elapsed_seconds": round(perf_counter() - started, 4),
            "memory_before": memory_before,
            "memory_after": memory_after,
            **details,
        },
    )


async def _broadcast_decision_events(
    response: RecommendationDecisionResponse,
    recommendation: ForecastRecommendation,
) -> None:
    """Publish decision updates without making a committed decision unavailable.

    Websocket clients are an auxiliary notification channel.  A disconnected or
    malformed client must not turn a successful operator decision into a failed
    request (or leave the request waiting indefinitely).
    """
    try:
        manager = get_streaming_service().connections
        await manager.broadcast("recommendation_decision", response)
        await manager.broadcast("recommendation_updated", recommendation_response(recommendation))
    except Exception:
        logger.exception(
            "recommendation_decision_broadcast_failed",
            extra={"recommendation_id": str(recommendation.id)},
        )


async def _broadcast_recommendation_event(event: str, data: object) -> None:
    try:
        await get_streaming_service().connections.broadcast(event, data)
    except Exception:
        logger.exception("recommendation_broadcast_failed", extra={"event": event})


def _schedule_broadcast(event: str, data: object) -> None:
    """Websocket delivery is auxiliary and must never extend an API response."""
    task = asyncio.create_task(_broadcast_recommendation_event(event, data))
    task.add_done_callback(
        lambda completed: completed.exception() if not completed.cancelled() else None
    )


def _rollback_decision(session: DatabaseSession, recommendation_id: UUID) -> None:
    """Rollback a failed decision transaction without masking its HTTP error."""
    try:
        session.rollback()
    except Exception:
        logger.exception(
            "recommendation_decision_rollback_failed",
            extra={"recommendation_id": str(recommendation_id)},
        )


def _persistence_unavailable_decision(
    recommendation_id: UUID, payload: RecommendationDecisionCreate
) -> RecommendationDecisionResponse:
    return RecommendationDecisionResponse(
        decision_id=UUID(int=0),
        recommendation_id=recommendation_id,
        timestamp=datetime.now(UTC),
        state=payload.operator_action,
        history_persistence_unavailable=True,
        history_persistence_message="history persistence unavailable",
        **payload.model_dump(),
    )


def _enrich_historical_evidence(
    rows: list[ForecastRecommendation], forecast: ForecastHistory
) -> None:
    """Populate optional evidence using a worker-owned read session."""
    request = forecast.request_data
    engine = InterventionEngine(ForecastingService(get_settings()))
    with SessionFactory() as history_session:
        for row in rows:
            evidence = engine._historical_evidence(
                history_session,
                str(request["current_grade"]),
                str(request["target_grade"]),
                row.affected_variables,
            )
            explanation = dict(row.explanation)
            explanation["historical_evidence"] = evidence.model_dump(mode="json")
            sources = list(explanation.get("inference_sources", []))
            if evidence.historical_effectiveness > 0:
                if "Historical Successful Transition" not in sources:
                    sources.append("Historical Successful Transition")
            else:
                sources = [item for item in sources if item != "Historical Successful Transition"]
            explanation["inference_sources"] = sources
            row.explanation = explanation


@router.post(
    "/interventions/recommendations",
    response_model=list[ForecastRecommendationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_recommendations(
    payload: RecommendationGenerationRequest, session: DatabaseSession
) -> list[ForecastRecommendationResponse]:
    started, memory_before = _endpoint_started("generate")
    try:
        forecast = session.get(ForecastHistory, payload.forecast_id)
    except Exception:
        logger.exception(
            "recommendation_forecast_lookup_failed",
            extra={"forecast_id": str(payload.forecast_id)},
        )
        _rollback_decision(session, payload.forecast_id)
        _endpoint_finished(
            "generate", started, memory_before, generated=0, persistence="unavailable"
        )
        return []
    if forecast is None:
        raise HTTPException(status_code=404, detail="Forecast not found.")
    try:
        rows = await run_in_threadpool(
            InterventionEngine(ForecastingService(get_settings())).generate,
            None,
            forecast,
            payload.max_results,
            payload.max_variables,
            False,
            False,
        )
    except Exception:
        logger.exception(
            "recommendation_generation_failed",
            extra={"forecast_id": str(payload.forecast_id)},
        )
        _rollback_decision(session, payload.forecast_id)
        _endpoint_finished(
            "generate", started, memory_before, generated=0, persistence="unavailable"
        )
        return []
    try:
        await run_in_threadpool(_enrich_historical_evidence, rows, forecast)
    except Exception:
        logger.exception("recommendation_historical_evidence_unavailable")
    try:
        responses = [recommendation_response(row) for row in rows]
    except Exception:
        logger.exception("recommendation_response_serialization_failed")
        _rollback_decision(session, payload.forecast_id)
        _endpoint_finished(
            "generate", started, memory_before, generated=0, persistence="unavailable"
        )
        return []
    try:
        for row in rows:
            session.add(row)
        session.commit()
        for row in rows:
            session.refresh(row)
    except Exception:
        _rollback_decision(session, payload.forecast_id)
        logger.exception(
            "recommendation_persistence_failed",
            extra={"forecast_id": str(payload.forecast_id)},
        )
    for response in responses:
        _schedule_broadcast("recommendation_created", response)
    _endpoint_finished("generate", started, memory_before, generated=len(responses))
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
    started, memory_before = _endpoint_started("history")
    try:
        now = datetime.now(UTC)
        expired = session.scalars(
            select(ForecastRecommendation).where(
                ForecastRecommendation.state.in_(["proposed", "delayed"]),
                ForecastRecommendation.expires_at < now,
            )
        )
        for row in expired:
            row.state = "expired"
        try:
            session.commit()
        except Exception:
            _rollback_decision(session, UUID(int=0))
            logger.exception("recommendation_history_expiry_persistence_failed")
        statement = select(ForecastRecommendation).order_by(
            ForecastRecommendation.created_at.desc()
        )
        if state:
            statement = statement.where(ForecastRecommendation.state == state)
        response = [recommendation_response(row) for row in session.scalars(statement.limit(limit))]
    except Exception:
        logger.exception("recommendation_history_unavailable")
        response = []
    _endpoint_finished("history", started, memory_before, returned=len(response))
    return response


@router.get("/interventions/audit", response_model=list[RecommendationAuditEvent])
def recommendation_audit(
    session: DatabaseSession,
    limit: int = Query(default=100, ge=1, le=300),
) -> list[RecommendationAuditEvent]:
    """Return the recorded recommendation lifecycle without inventing workflow events."""
    try:
        recommendations = list(
            session.scalars(
                select(ForecastRecommendation)
                .order_by(ForecastRecommendation.created_at.desc())
                .limit(limit)
            )
        )
        recommendation_by_id = {row.id: row for row in recommendations}
        ids = list(recommendation_by_id)
        if not ids:
            return []
        decisions = list(
            session.scalars(
                select(RecommendationDecision).where(
                    RecommendationDecision.recommendation_id.in_(ids)
                )
            )
        )
        outcomes = list(
            session.scalars(
                select(RecommendationOutcome).where(
                    RecommendationOutcome.recommendation_id.in_(ids)
                )
            )
        )
        events = [
            RecommendationAuditEvent(
                timestamp=row.created_at,
                event="Recommendation Generated",
                recommendation_id=row.id,
                summary=(
                    "Forecast identified an intervention for "
                    + ", ".join(row.affected_variables)
                    + "."
                ),
            )
            for row in recommendations
        ]
        for decision in decisions:
            row = recommendation_by_id[decision.recommendation_id]
            action = decision.operator_action.capitalize()
            changes = ", ".join(item["variable"].replace("_", " ") for item in row.changes)
            events.append(
                RecommendationAuditEvent(
                    timestamp=decision.created_at,
                    event=f"Operator {action}",
                    recommendation_id=decision.recommendation_id,
                    summary=decision.reason or f"Operator {decision.operator_action} {changes}.",
                )
            )
        for outcome in outcomes:
            row = recommendation_by_id[outcome.recommendation_id]
            reduction = (
                float(row.metrics["crossing_probability_before"])
                - float(row.metrics["crossing_probability_after"])
            ) * 100
            events.append(
                RecommendationAuditEvent(
                    timestamp=outcome.created_at,
                    event="Outcome Evaluated",
                    recommendation_id=outcome.recommendation_id,
                    summary=(
                        "Recorded forecast crossing-probability change: "
                        f"{reduction:+.2f} percentage points."
                    ),
                )
            )
        return sorted(events, key=lambda event: event.timestamp, reverse=True)[:limit]
    except Exception:
        logger.exception("recommendation_audit_history_unavailable")
        return []


@router.get(
    "/interventions/recommendations/{recommendation_id}",
    response_model=ForecastRecommendationResponse,
)
def get_recommendation(
    recommendation_id: UUID, session: DatabaseSession
) -> ForecastRecommendationResponse:
    try:
        row = session.get(ForecastRecommendation, recommendation_id)
        if row is not None:
            return recommendation_response(row)
    except Exception:
        logger.exception(
            "recommendation_lookup_failed",
            extra={"recommendation_id": str(recommendation_id)},
        )
        _rollback_decision(session, recommendation_id)

    raise HTTPException(status_code=404, detail="Recommendation not found.")


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
    started, memory_before = _endpoint_started("decision")
    try:
        row = session.get(ForecastRecommendation, recommendation_id)
    except Exception:
        logger.exception(
            "recommendation_decision_lookup_failed",
            extra={"recommendation_id": str(recommendation_id)},
        )
        response = _persistence_unavailable_decision(recommendation_id, payload)
        _endpoint_finished("decision", started, memory_before, persistence="unavailable")
        return response
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if row.state in {"expired", "evaluated"}:
        raise HTTPException(status_code=409, detail=f"Recommendation is {row.state}.")
    if payload.operator_action == "modified" and not payload.modified_values:
        raise HTTPException(status_code=422, detail="Modified values are required.")
    if payload.operator_action == "delayed" and not payload.delay_duration_seconds:
        raise HTTPException(status_code=422, detail="Delay duration is required.")
    try:
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
            row.expires_at = datetime.now(UTC) + timedelta(
                seconds=payload.delay_duration_seconds or 0
            )
        session.add(decision)
        session.commit()
        session.refresh(decision)
        session.refresh(row)
    except SQLAlchemyError:
        _rollback_decision(session, recommendation_id)
        logger.exception(
            "recommendation_decision_persistence_failed",
            extra={"recommendation_id": str(recommendation_id)},
        )
        response = _persistence_unavailable_decision(recommendation_id, payload)
        _endpoint_finished("decision", started, memory_before, persistence="unavailable")
        return response
    except Exception:
        _rollback_decision(session, recommendation_id)
        logger.exception(
            "recommendation_decision_failed",
            extra={"recommendation_id": str(recommendation_id)},
        )
        response = _persistence_unavailable_decision(recommendation_id, payload)
        _endpoint_finished("decision", started, memory_before, persistence="unavailable")
        return response
    response = RecommendationDecisionResponse(
        decision_id=decision.id,
        recommendation_id=row.id,
        timestamp=decision.created_at,
        state=row.state,
        **payload.model_dump(),
    )
    _schedule_broadcast("recommendation_decision", response)
    _schedule_broadcast("recommendation_updated", recommendation_response(row))
    _endpoint_finished("decision", started, memory_before, persistence="available")
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
    started, memory_before = _endpoint_started("outcome")
    try:
        row = session.get(ForecastRecommendation, recommendation_id)
    except Exception:
        logger.exception(
            "recommendation_outcome_lookup_failed",
            extra={"recommendation_id": str(recommendation_id)},
        )
        response = RecommendationOutcomeResponse(
            outcome_id=UUID(int=0),
            recommendation_id=recommendation_id,
            metrics={},
            evaluated_at=datetime.now(UTC),
            history_persistence_unavailable=True,
            history_persistence_message="history persistence unavailable",
        )
        _endpoint_finished("outcome", started, memory_before, persistence="unavailable")
        return response
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    try:
        existing = session.scalar(
            select(RecommendationOutcome).where(
                RecommendationOutcome.recommendation_id == recommendation_id
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Outcome already evaluated.")
    except HTTPException:
        raise
    except Exception:
        logger.exception("recommendation_outcome_history_unavailable")
    if row.state not in {"accepted", "applied"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Outcome evaluation requires an accepted or applied recommendation; "
                f"current state is {row.state}."
            ),
        )
    metrics = await run_in_threadpool(OutcomeEvaluator().evaluate, row, payload.observations)
    outcome = RecommendationOutcome(
        recommendation_id=row.id,
        observations=[point.model_dump(mode="json") for point in payload.observations],
        metrics=metrics,
    )
    row.state = "evaluated"
    try:
        session.add(outcome)
        session.commit()
        session.refresh(outcome)
    except Exception:
        _rollback_decision(session, recommendation_id)
        logger.exception(
            "recommendation_outcome_persistence_failed",
            extra={"recommendation_id": str(recommendation_id)},
        )
        response = RecommendationOutcomeResponse(
            outcome_id=UUID(int=0), recommendation_id=recommendation_id, metrics=metrics,
            evaluated_at=datetime.now(UTC), history_persistence_unavailable=True,
            history_persistence_message="history persistence unavailable",
        )
        _schedule_broadcast("recommendation_outcome", response)
        _endpoint_finished("outcome", started, memory_before, persistence="unavailable")
        return response
    response = RecommendationOutcomeResponse(
        outcome_id=outcome.id,
        recommendation_id=row.id,
        metrics=metrics,
        evaluated_at=outcome.created_at,
    )
    _schedule_broadcast("recommendation_outcome", response)
    _endpoint_finished("outcome", started, memory_before, persistence="available")
    return response


@router.get("/interventions/effectiveness", response_model=EffectivenessResponse)
def effectiveness(session: DatabaseSession) -> EffectivenessResponse:
    try:
        return OutcomeEvaluator().effectiveness(session)
    except Exception:
        logger.exception("recommendation_effectiveness_history_unavailable")
        return EffectivenessResponse(
            evaluated_count=0,
            crossing_avoidance_rate=0,
            crossing_delay_rate=0,
            mean_prediction_error=0,
            mean_deviation_improvement=0,
            mean_stabilization_improvement=0,
        )
