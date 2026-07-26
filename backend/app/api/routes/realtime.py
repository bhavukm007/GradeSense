from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.dependencies import DatabaseSession
from app.models.intelligence import AlertHistory, OperatorFeedback, PredictionHistory
from app.schemas.realtime import (
    AlertResponse,
    DriftResponse,
    FeedbackCreate,
    FeedbackResponse,
    LiveMetricsResponse,
    RollingWindow,
    StreamStatusResponse,
)
from app.services.streaming import get_streaming_service

router = APIRouter(tags=["real-time monitoring"])


def alert_response(row: AlertHistory) -> AlertResponse:
    return AlertResponse(
        id=row.id,
        severity=row.severity,
        title=row.title,
        description=row.description,
        timestamp=row.created_at,
        affected_variables=row.affected_variables,
        suggested_action=row.suggested_action,
        acknowledged=row.acknowledged,
        acknowledged_at=row.acknowledged_at,
        prediction_id=row.prediction_id,
    )


@router.get("/alerts", response_model=list[AlertResponse])
def alerts(
    session: DatabaseSession,
    acknowledged: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AlertResponse]:
    statement = select(AlertHistory).order_by(AlertHistory.created_at.desc()).limit(limit)
    if acknowledged is not None:
        statement = statement.where(AlertHistory.acknowledged == acknowledged)
    return [alert_response(row) for row in session.scalars(statement)]


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: UUID, session: DatabaseSession) -> AlertResponse:
    row = session.get(AlertHistory, alert_id)
    if row is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Alert not found.")
    row.acknowledged = True
    row.acknowledged_at = datetime.now(UTC)
    session.commit()
    session.refresh(row)
    return alert_response(row)


@router.get("/feedback", response_model=list[FeedbackResponse])
def feedback(session: DatabaseSession) -> list[FeedbackResponse]:
    rows = session.scalars(
        select(OperatorFeedback).order_by(OperatorFeedback.created_at.desc()).limit(100)
    )
    return [
        FeedbackResponse(
            id=row.id,
            prediction_id=row.prediction_id,
            outcome=row.outcome,
            notes=row.notes,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
def create_feedback(payload: FeedbackCreate, session: DatabaseSession) -> FeedbackResponse:
    if session.get(PredictionHistory, payload.prediction_id) is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Prediction not found.")
    row = OperatorFeedback(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return FeedbackResponse(
        id=row.id,
        prediction_id=row.prediction_id,
        outcome=row.outcome,
        notes=row.notes,
        created_at=row.created_at,
    )


@router.get("/stream/status", response_model=StreamStatusResponse)
def stream_status() -> StreamStatusResponse:
    return get_streaming_service().status_response()


@router.get("/stream/statistics", response_model=list[RollingWindow])
@router.get("/metrics/rolling", response_model=list[RollingWindow])
def rolling_metrics() -> list[RollingWindow]:
    return get_streaming_service().rolling()


@router.get("/metrics/live", response_model=LiveMetricsResponse)
def live_metrics() -> LiveMetricsResponse:
    return get_streaming_service().latest


@router.get("/drift", response_model=DriftResponse | None)
def drift() -> DriftResponse | None:
    return get_streaming_service().latest.drift


async def websocket_endpoint(websocket: WebSocket) -> None:
    service = get_streaming_service()
    await service.connections.connect(websocket)
    await service.connections.broadcast("system_status", service.status_response())
    try:
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        service.connections.disconnect(websocket)


router.add_api_websocket_route("/ws/live", websocket_endpoint)
router.add_api_websocket_route("/ws/dashboard", websocket_endpoint)
