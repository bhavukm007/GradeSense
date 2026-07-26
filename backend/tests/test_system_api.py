from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["documentation_url"] == "/docs"


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["environment"] == "test"


def test_version(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == "0.2.0"


def test_openapi_exposes_phase_two_routes(client: TestClient) -> None:
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {
        "/",
        "/health",
        "/version",
        "/predict",
        "/recommend",
        "/correlations",
        "/dataset/statistics",
        "/dataset/regenerate",
        "/model/info",
        "/history/predictions",
        "/history/recommendations",
        "/alerts",
        "/alerts/{alert_id}/acknowledge",
        "/stream/status",
        "/stream/statistics",
        "/drift",
        "/feedback",
        "/metrics/live",
        "/metrics/rolling",
        "/forecast",
        "/forecast/{forecast_id}",
        "/forecast/simulate",
        "/forecast/history",
        "/relationships/discovery",
    }.issubset(paths)
    assert {
        "/interventions/recommendations",
        "/interventions/recommendations/{recommendation_id}",
        "/interventions/recommendations/{recommendation_id}/decisions",
        "/interventions/recommendations/{recommendation_id}/outcome",
        "/interventions/effectiveness",
        "/demo/seed",
    }.issubset(paths)


def test_demo_seed_populates_judge_workflow(client: TestClient) -> None:
    response = client.post("/demo/seed")
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["predictions"] >= 3
    assert payload["recommendations"] >= 3
    assert payload["decisions"] >= 3
    assert payload["outcomes"] >= 1
    assert client.get("/interventions/effectiveness").json()["evaluated_count"] >= 1
