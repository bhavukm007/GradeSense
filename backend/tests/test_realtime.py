from uuid import UUID

import pandas as pd
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.database.session import SessionFactory
from app.schemas.intelligence import PredictionResponse, ProcessInput
from app.services.alert import AlertService
from app.services.drift import DriftService
from tests.test_intelligence_api import PROCESS_INPUT


def test_stream_status_rolling_metrics_and_websocket(client: TestClient) -> None:
    status = client.get("/stream/status")
    assert status.status_code == 200
    assert status.json()["status"] == "running"

    rolling = client.get("/metrics/rolling")
    assert rolling.status_code == 200
    assert [item["window"] for item in rolling.json()] == [
        "1 minute",
        "10 minutes",
        "1 hour",
    ]

    with client.websocket_connect("/ws/live") as websocket:
        event = websocket.receive_json()
        assert event["event"] == "system_status"
        assert event["data"]["status"] == "running"


def test_alert_engine_persistence_and_acknowledgement(client: TestClient) -> None:
    prediction_payload = client.post("/predict", json=PROCESS_INPUT).json()
    prediction = PredictionResponse.model_validate(prediction_payload)
    sample = ProcessInput.model_validate({**PROCESS_INPUT, "moisture": 9.2})
    with SessionFactory() as session:
        alerts = AlertService().evaluate(session, sample, prediction)
    moisture_alert = next(alert for alert in alerts if alert.title == "Abnormal moisture")

    response = client.post(f"/alerts/{moisture_alert.id}/acknowledge")
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True


def test_feedback_api_links_to_prediction(client: TestClient) -> None:
    prediction_id = client.post("/predict", json=PROCESS_INPUT).json()["prediction_id"]
    response = client.post(
        "/feedback",
        json={
            "prediction_id": prediction_id,
            "outcome": "recommendation_accepted",
            "notes": "Applied during the transition.",
        },
    )
    assert response.status_code == 201
    assert UUID(response.json()["prediction_id"]) == UUID(prediction_id)
    assert any(item["id"] == response.json()["id"] for item in client.get("/feedback").json())


def test_drift_detection_uses_training_distribution() -> None:
    training = pd.read_csv(get_settings().dataset_path)
    shifted = [
        ProcessInput.model_validate(
            {
                **PROCESS_INPUT,
                "machine_speed": 1190,
                "moisture": 9.8,
                "steam_pressure": 9.3,
            }
        )
        for _ in range(12)
    ]
    result = DriftService().calculate(shifted, training, [0.2, 0.8] * 6)
    assert result.score > 0
    assert result.drifting_variables
    assert result.severity in {"watch", "warning", "critical"}
