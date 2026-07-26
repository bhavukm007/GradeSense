from fastapi.testclient import TestClient

PROCESS_INPUT = {
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
}


def test_prediction_endpoint_returns_model_output_and_explanation(
    client: TestClient,
) -> None:
    response = client.post("/predict", json=PROCESS_INPUT)
    assert response.status_code == 200
    payload = response.json()
    assert 0 <= payload["quality_score"] <= 100
    assert 0 <= payload["off_spec_probability"] <= 1
    assert payload["expected_stabilization_time"] > 0
    assert len(payload["explanation"]["top_contributing_features"]) == 5
    assert len(payload["explanation"]["feature_importance"]) == 15
    assert payload["explanation"]["summary"]


def test_recommendations_are_model_evaluated_and_persisted(client: TestClient) -> None:
    response = client.post("/recommend", json=PROCESS_INPUT)
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation_id"]
    assert payload["prediction"]["prediction_id"]
    assert payload["recommendations"]
    assert all(item["expected_improvement"] >= 0 for item in payload["recommendations"])
    assert all(item["affected_variables"] for item in payload["recommendations"])
    assert len({item["text"] for item in payload["recommendations"]}) == len(
        payload["recommendations"]
    )


def test_dataset_and_model_endpoints(client: TestClient) -> None:
    statistics = client.get("/dataset/statistics")
    assert statistics.status_code == 200
    assert statistics.json()["record_count"] == 1500
    assert "quality_score" in statistics.json()["numeric_summary"]

    correlations = client.get("/correlations", params={"limit": 4})
    assert correlations.status_code == 200
    assert len(correlations.json()["strongest_positive_correlations"]) == 4
    assert len(correlations.json()["strongest_negative_correlations"]) == 4

    model_info = client.get("/model/info")
    assert model_info.status_code == 200
    assert model_info.json()["model_type"] == "RandomForestRegressor"
    assert model_info.json()["target_metrics"]["off_spec_probability_r2"] > 0.7


def test_input_validation_rejects_unsafe_process_values(client: TestClient) -> None:
    invalid = {**PROCESS_INPUT, "steam_pressure": 20}
    response = client.post("/predict", json=invalid)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_history_endpoints_return_persisted_records(client: TestClient) -> None:
    prediction = client.post("/predict", json=PROCESS_INPUT).json()
    recommendation = client.post("/recommend", json=PROCESS_INPUT).json()

    predictions = client.get("/history/predictions", params={"page_size": 1})
    assert predictions.status_code == 200
    assert predictions.json()["pagination"]["total"] >= 2
    assert len(predictions.json()["items"]) == 1
    assert predictions.json()["items"][0]["prediction_id"]

    recommendations = client.get("/history/recommendations", params={"page_size": 10})
    assert recommendations.status_code == 200
    assert recommendations.json()["pagination"]["total"] >= 1
    assert any(
        item["recommendation_id"] == recommendation["recommendation_id"]
        for item in recommendations.json()["items"]
    )
    assert prediction["prediction_id"]


def test_dataset_regeneration_endpoint_trains_new_model(client: TestClient) -> None:
    previous_version = client.get("/model/info").json()["model_version"]
    response = client.post(
        "/dataset/regenerate",
        json={"records": 20_000, "seed": 123},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["records"] == 20_000
    assert payload["model_version"] != previous_version
    assert payload["training_metrics"]["quality_score_r2"] > 0.8
