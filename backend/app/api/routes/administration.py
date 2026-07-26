import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy import func, select

from app.api.dependencies import DatabaseSession
from app.config.settings import get_settings
from app.models.intelligence import (
    AlertHistory,
    AuditLog,
    ForecastHistory,
    ForecastRecommendation,
    OperatorFeedback,
    RecommendationDecision,
    RecommendationOutcome,
    RegisteredModel,
    RollingMetricSnapshot,
)
from app.schemas.administration import (
    AuditResponse,
    ExportDescriptor,
    ExportRequest,
    ModelAction,
    ModelRegister,
    RegisteredModelResponse,
    RuntimeConfigResponse,
)
from app.services.demo import DemoSeedService
from app.services.operations import (
    AuditService,
    RuntimeConfigService,
    metrics_service,
)
from app.services.registry import ModelRegistryService, ModelValidationError
from app.services.streaming import get_streaming_service

router = APIRouter(tags=["production administration"])


@router.post("/demo/seed", status_code=201)
def seed_honeywell_demo(session: DatabaseSession) -> dict[str, int]:
    return DemoSeedService(get_settings()).seed(session)


def model_response(row: RegisteredModel) -> RegisteredModelResponse:
    return RegisteredModelResponse(
        model_id=row.id,
        created_at=row.created_at,
        version=row.version,
        name=row.name,
        model_kind=row.model_kind,
        algorithm=row.algorithm,
        trained_at=row.trained_at,
        dataset_checksum=row.dataset_checksum,
        feature_schema_checksum=row.feature_schema_checksum,
        artifact_checksum=row.artifact_checksum,
        artifact_path=row.artifact_path,
        metrics=row.metrics,
        training_parameters=row.training_parameters,
        description=row.description,
        status=row.status,
    )


@router.get("/models", response_model=list[RegisteredModelResponse])
@router.get("/admin/models", response_model=list[RegisteredModelResponse])
def models(session: DatabaseSession) -> list[RegisteredModelResponse]:
    return [
        model_response(row)
        for row in session.scalars(
            select(RegisteredModel).order_by(RegisteredModel.created_at.desc())
        )
    ]


@router.get("/models/active", response_model=list[RegisteredModelResponse])
def active_models(session: DatabaseSession) -> list[RegisteredModelResponse]:
    return [
        model_response(row)
        for row in session.scalars(
            select(RegisteredModel).where(RegisteredModel.status == "active")
        )
    ]


@router.get("/models/{model_id}", response_model=RegisteredModelResponse)
def get_model(model_id: UUID, session: DatabaseSession) -> RegisteredModelResponse:
    row = session.get(RegisteredModel, model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")
    return model_response(row)


def registry_action(
    session: DatabaseSession,
    action: str,
    callback,
    request_id: str | None,
) -> RegisteredModelResponse:
    try:
        row = callback()
    except ModelValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    AuditService().record(
        session,
        action=f"model_{action}",
        entity="model",
        entity_id=str(row.id),
        details={"version": row.version, "kind": row.model_kind},
        request_id=request_id,
    )
    return model_response(row)


@router.post("/models/register", response_model=RegisteredModelResponse, status_code=201)
def register_model(
    payload: ModelRegister, request: Request, session: DatabaseSession
) -> RegisteredModelResponse:
    return registry_action(
        session,
        "registration",
        lambda: ModelRegistryService().register(session, payload),
        getattr(request.state, "request_id", None),
    )


@router.post("/models/promote", response_model=RegisteredModelResponse)
def promote_model(
    payload: ModelAction, request: Request, session: DatabaseSession
) -> RegisteredModelResponse:
    return registry_action(
        session,
        "promotion",
        lambda: ModelRegistryService().promote(session, payload.model_id),
        getattr(request.state, "request_id", None),
    )


@router.post("/models/archive", response_model=RegisteredModelResponse)
def archive_model(
    payload: ModelAction, request: Request, session: DatabaseSession
) -> RegisteredModelResponse:
    return registry_action(
        session,
        "archive",
        lambda: ModelRegistryService().archive(session, payload.model_id),
        getattr(request.state, "request_id", None),
    )


def operational_metrics() -> dict[str, Any]:
    stream = get_streaming_service()
    return metrics_service.snapshot(
        active_websockets=len(stream.connections.clients),
        stream_samples=stream.sample_count,
    )


@router.get("/admin/metrics")
def metrics() -> dict[str, Any]:
    return operational_metrics()


@router.get("/admin/config", response_model=RuntimeConfigResponse)
def config(session: DatabaseSession) -> RuntimeConfigResponse:
    return RuntimeConfigService().get(session, get_settings())


@router.put("/admin/config", response_model=RuntimeConfigResponse)
def update_config(
    payload: RuntimeConfigResponse, request: Request, session: DatabaseSession
) -> RuntimeConfigResponse:
    result = RuntimeConfigService().update(session, payload)
    get_streaming_service().settings.stream_interval_seconds = payload.stream_speed_seconds
    AuditService().record(
        session,
        "configuration_change",
        "runtime_configuration",
        details=payload.model_dump(mode="json"),
        actor=request.headers.get("X-Actor", "operator"),
        request_id=getattr(request.state, "request_id", None),
    )
    return result


def detailed_health(session: DatabaseSession) -> dict[str, Any]:
    settings = get_settings()
    database_ok, database_latency = metrics_service.database_probe(session)
    active = list(
        session.scalars(select(RegisteredModel).where(RegisteredModel.status == "active"))
    )
    active_kinds = {row.model_kind for row in active}
    active_paths = {row.model_kind: Path(row.artifact_path) for row in active}
    stream = get_streaming_service()
    metric = operational_metrics()
    checks = {
        "api": {"status": "healthy"},
        "database": {
            "status": "healthy" if database_ok else "unhealthy",
            "latency_ms": database_latency,
        },
        "forecast_service": {
            "status": (
                "healthy"
                if active_paths.get("forecast", settings.forecast_model_path).exists()
                else "degraded"
            )
        },
        "intervention_service": {"status": "healthy" if "forecast" in active_kinds else "degraded"},
        "streaming_worker": {"status": stream.status},
        "websockets": {
            "status": "healthy",
            "active_connections": len(stream.connections.clients),
        },
        "model_registry": {
            "status": "healthy" if active else "degraded",
            "active_models": len(active),
        },
        "datasets": {
            "snapshot": settings.dataset_path.exists(),
            "sequential": settings.sequential_dataset_path.exists(),
        },
        "resources": {
            "cpu_percent": metric["cpu_percent"],
            "memory_percent": metric["memory_percent"],
            "disk_used_percent": (
                metric["disk_used_bytes"] / max(metric["disk_total_bytes"], 1) * 100
            ),
        },
    }
    return {
        "status": (
            "healthy"
            if database_ok and {"prediction", "forecast"}.issubset(active_kinds)
            else "degraded"
        ),
        "application_version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": metric["uptime_seconds"],
        "checks": checks,
    }


@router.get("/admin/health")
def admin_health(session: DatabaseSession) -> dict[str, Any]:
    return detailed_health(session)


@router.get("/admin/system")
def admin_system(session: DatabaseSession) -> dict[str, Any]:
    return {
        "health": detailed_health(session),
        "metrics": operational_metrics(),
        "configuration": RuntimeConfigService().get(session, get_settings()),
    }


@router.get("/admin/audit", response_model=list[AuditResponse])
def audit(
    session: DatabaseSession,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[AuditResponse]:
    return [
        AuditService.response(row)
        for row in session.scalars(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        )
    ]


EXPORT_MODELS = {
    "forecasts": ForecastHistory,
    "recommendations": ForecastRecommendation,
    "decisions": RecommendationDecision,
    "outcomes": RecommendationOutcome,
    "alerts": AlertHistory,
    "feedback": OperatorFeedback,
    "metrics": RollingMetricSnapshot,
    "models": RegisteredModel,
    "audit": AuditLog,
}


@router.get("/admin/exports", response_model=list[ExportDescriptor])
def exports(session: DatabaseSession) -> list[ExportDescriptor]:
    return [
        ExportDescriptor(
            resource=name,
            formats=["json", "csv"],
            row_count=session.scalar(select(func.count(model.id))) or 0,
        )
        for name, model in EXPORT_MODELS.items()
    ]


@router.post("/admin/export")
def create_export(payload: ExportRequest, request: Request, session: DatabaseSession) -> Response:
    rows = list(session.scalars(select(EXPORT_MODELS[payload.resource])))
    records = [
        {
            column.name: jsonable_encoder(getattr(row, column.name))
            for column in row.__table__.columns
        }
        for row in rows
    ]
    AuditService().record(
        session,
        "export",
        payload.resource,
        details={"format": payload.format, "row_count": len(records)},
        actor=request.headers.get("X-Actor", "operator"),
        request_id=getattr(request.state, "request_id", None),
    )
    filename = f"gradesense-{payload.resource}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    if payload.format == "json":
        return Response(
            json.dumps(records, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )
    output = io.StringIO()
    fieldnames = list(records[0]) if records else ["no_records"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                key: json.dumps(value) if isinstance(value, (dict, list)) else value
                for key, value in record.items()
            }
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )
