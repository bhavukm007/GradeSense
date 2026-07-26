from copy import deepcopy
from pathlib import Path

import joblib
import pytest

from app.config.settings import get_settings
from app.domain.features import PROCESS_FEATURES
from app.services.forecasting.model import ForecastArtifactService
from app.services.intelligence import IntelligenceService
from app.services.registry import file_checksum, schema_checksum


def test_registry_bootstrap_and_active_models(client) -> None:
    models = client.get("/models")
    assert models.status_code == 200
    kinds = {item["model_kind"] for item in models.json()}
    assert {"prediction", "forecast"}.issubset(kinds)
    active = client.get("/models/active")
    assert active.status_code == 200
    assert {"prediction", "forecast"} == {item["model_kind"] for item in active.json()}
    for item in active.json():
        assert client.get(f"/models/{item['model_id']}").status_code == 200


def test_register_promote_archive_and_dynamic_switch(client) -> None:
    settings = get_settings()
    source = settings.model_path.resolve()
    source_artifact = joblib.load(source)
    artifact = deepcopy(source_artifact)
    artifact["version"] = f"{artifact['version']}-phase07-test"
    candidate = Path("tests/.artifacts/registry_candidate.joblib").resolve()
    joblib.dump(artifact, candidate)
    payload = {
        "version": artifact["version"],
        "name": "Registry switching test",
        "model_kind": "prediction",
        "algorithm": "RandomForestRegressor",
        "trained_at": artifact["trained_at"].isoformat(),
        "dataset_checksum": artifact["dataset_checksum"],
        "feature_schema_checksum": schema_checksum(PROCESS_FEATURES),
        "artifact_checksum": file_checksum(candidate),
        "artifact_path": str(candidate),
        "metrics": artifact["metrics"],
        "training_parameters": {"source": "existing test artifact"},
        "description": "Checksum-valid test registry candidate.",
        "status": "experimental",
    }
    registered = client.post("/models/register", json=payload)
    assert registered.status_code == 201, registered.text
    candidate_id = registered.json()["model_id"]
    promoted = client.post("/models/promote", json={"model_id": candidate_id})
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["status"] == "active"
    assert any(item["model_id"] == candidate_id for item in client.get("/models/active").json())
    prediction = client.post(
        "/predict",
        json={
            "current_grade": "Kraft",
            "target_grade": "CopyPaper",
            "machine_speed": 880,
            "steam_pressure": 5.4,
            "dryer_temperature": 104,
            "moisture": 7.4,
            "basis_weight": 86,
            "caliper": 112,
            "pulp_consistency": 3.5,
            "stock_flow": 3400,
            "refining_energy": 160,
            "headbox_pressure": 3.8,
            "reel_tension": 5.2,
            "ambient_temperature": 30,
            "humidity": 72,
        },
    )
    assert prediction.status_code == 200
    assert prediction.json()["model_version"] == artifact["version"]
    assert client.post("/models/archive", json={"model_id": candidate_id}).status_code == 422
    restore_artifact = deepcopy(source_artifact)
    restore_artifact["version"] = f"{source_artifact['version']}-phase07-restore"
    restore_path = Path("tests/.artifacts/registry_restore.joblib").resolve()
    joblib.dump(restore_artifact, restore_path)
    restore_payload = {
        **payload,
        "version": restore_artifact["version"],
        "name": "Registry restoration test",
        "artifact_checksum": file_checksum(restore_path),
        "artifact_path": str(restore_path),
    }
    restore_registration = client.post("/models/register", json=restore_payload)
    assert restore_registration.status_code == 201, restore_registration.text
    restored = client.post(
        "/models/promote",
        json={"model_id": restore_registration.json()["model_id"]},
    )
    assert restored.status_code == 200, restored.text
    archived = client.post("/models/archive", json={"model_id": candidate_id})
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_invalid_registry_candidate_is_rejected(client) -> None:
    payload = {
        "version": "missing",
        "name": "Invalid",
        "model_kind": "forecast",
        "algorithm": "none",
        "trained_at": "2026-07-25T00:00:00Z",
        "dataset_checksum": "x",
        "feature_schema_checksum": "x",
        "artifact_checksum": "x",
        "artifact_path": "tests/.artifacts/does-not-exist.joblib",
        "metrics": {"mae": 1},
        "training_parameters": {},
        "description": "Must fail validation.",
        "status": "experimental",
    }
    assert client.post("/models/register", json=payload).status_code == 422


def test_metrics_health_and_admin_endpoints(client) -> None:
    client.get("/health")
    metrics = client.get("/admin/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["request_count"] >= 1
    assert body["response_count"] >= 1
    assert body["cpu_percent"] >= 0
    assert body["memory_bytes"] > 0
    assert body["disk_total_bytes"] > 0
    health = client.get("/admin/health")
    assert health.status_code == 200
    assert health.json()["checks"]["database"]["latency_ms"] >= 0
    assert client.get("/admin/system").status_code == 200
    assert client.get("/admin/models").status_code == 200


def test_runtime_configuration_reload_and_audit(client) -> None:
    original = client.get("/admin/config").json()
    changed = {**original, "stream_speed_seconds": 1.25, "recommendation_limit": 3}
    response = client.put("/admin/config", json=changed, headers={"X-Actor": "shift-supervisor"})
    assert response.status_code == 200
    assert client.get("/admin/config").json()["stream_speed_seconds"] == 1.25
    audit = client.get("/admin/audit")
    assert audit.status_code == 200
    assert any(
        item["action"] == "configuration_change" and item["actor"] == "shift-supervisor"
        for item in audit.json()
    )
    assert client.put("/admin/config", json=original).status_code == 200


def test_json_csv_exports_and_export_audit(client) -> None:
    catalog = client.get("/admin/exports")
    assert catalog.status_code == 200
    assert {"forecasts", "models", "audit"}.issubset({item["resource"] for item in catalog.json()})
    exported_json = client.post("/admin/export", json={"resource": "models", "format": "json"})
    assert exported_json.status_code == 200
    assert exported_json.headers["content-type"].startswith("application/json")
    exported_csv = client.post("/admin/export", json={"resource": "audit", "format": "csv"})
    assert exported_csv.status_code == 200
    assert exported_csv.headers["content-type"].startswith("text/csv")
    assert any(item["action"] == "export" for item in client.get("/admin/audit").json())


def test_security_middleware_request_ids_headers_and_payload_limit(client) -> None:
    response = client.get("/health", headers={"X-Request-ID": "phase07-request"})
    assert response.headers["X-Request-ID"] == "phase07-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    oversized = client.post(
        "/predict",
        content=b"x" * 2_000_001,
        headers={"Content-Type": "application/json"},
    )
    assert oversized.status_code == 413


def test_startup_readiness_never_generates_missing_artifacts() -> None:
    missing_dataset = Path("tests/.artifacts/intentionally_missing.csv")
    missing_model = Path("tests/.artifacts/intentionally_missing.joblib")
    settings = get_settings().model_copy(
        update={
            "dataset_path": missing_dataset,
            "model_path": missing_model,
        }
    )
    with pytest.raises(RuntimeError, match="will not generate or retrain"):
        from app.database.session import SessionFactory

        with SessionFactory() as session:
            IntelligenceService(settings, session).ensure_ready()
    assert not settings.dataset_path.exists()
    assert not settings.model_path.exists()


def test_forecast_artifact_is_cached_by_immutable_path() -> None:
    path = get_settings().forecast_model_path.resolve()
    first = ForecastArtifactService(path).load()
    second = ForecastArtifactService(path).load()
    assert first is second
