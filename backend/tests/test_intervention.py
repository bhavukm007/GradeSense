import asyncio

from app.schemas.forecasting import ForecastRequest, InterventionChange
from app.services.constraints import ConstraintEngine
from app.services.streaming import ConnectionManager
from tests.test_forecasting import request_payload


def create_forecast(client) -> dict:
    response = client.post("/forecast", json=request_payload())
    assert response.status_code == 200
    return response.json()


def test_constraint_validation_rejects_unsafe_combinations() -> None:
    request = ForecastRequest.model_validate(request_payload())
    result = ConstraintEngine().validate(
        request,
        [
            InterventionChange(variable="dryer_temperature", value=140),
            InterventionChange(variable="steam_pressure", value=9),
        ],
    )
    assert not result.feasible
    assert result.violations


def test_forecast_driven_generation_persistence_and_decision(client) -> None:
    forecast = create_forecast(client)
    created = client.post(
        "/interventions/recommendations",
        json={"forecast_id": forecast["forecast_id"], "max_results": 3, "max_variables": 2},
    )
    assert created.status_code == 201, created.text
    recommendations = created.json()
    assert recommendations
    assert all(item["constraint_validation"]["feasible"] for item in recommendations)
    assert all(item["baseline_trajectory"] for item in recommendations)
    assert all(item["intervention_trajectory"] for item in recommendations)
    assert all(item["metrics"]["estimated_improvement"] > 0 for item in recommendations)
    assert all("Forecast" in item["inference_sources"] for item in recommendations)
    assert all("Historical Trend" in item["inference_sources"] for item in recommendations)
    assert all("historical_evidence" in item for item in recommendations)
    recommendation = recommendations[0]
    stored = client.get(f"/interventions/recommendations/{recommendation['recommendation_id']}")
    assert stored.status_code == 200
    decision = client.post(
        f"/interventions/recommendations/{recommendation['recommendation_id']}/decisions",
        json={"operator_action": "accepted", "reason": "Best forecast improvement"},
    )
    assert decision.status_code == 201, decision.text
    assert decision.json()["state"] == "accepted"


def test_historical_evidence_and_recipe_attribution(client) -> None:
    forecast = create_forecast(client)
    first = client.post(
        "/interventions/recommendations",
        json={"forecast_id": forecast["forecast_id"], "max_results": 3},
    ).json()
    recipe_recommendation = next(
        (item for item in first if item["constraint_validation"]["recipe_rules"]),
        first[0],
    )
    accepted = client.post(
        f"/interventions/recommendations/{recipe_recommendation['recommendation_id']}/decisions",
        json={"operator_action": "accepted", "reason": "Historical evidence fixture"},
    )
    assert accepted.status_code == 201
    outcome = client.post(
        f"/interventions/recommendations/{recipe_recommendation['recommendation_id']}/outcome",
        json={"observations": recipe_recommendation["intervention_trajectory"]},
    )
    assert outcome.status_code == 201

    later = client.post(
        "/interventions/recommendations",
        json={"forecast_id": forecast["forecast_id"], "max_results": 5},
    ).json()
    matched = [
        item
        for item in later
        if set(item["affected_variables"]).intersection(recipe_recommendation["affected_variables"])
    ]
    assert matched
    assert matched[0]["historical_evidence"]["similar_transition_count"] >= 1
    assert matched[0]["historical_evidence"]["historical_acceptance_rate"] > 0
    assert matched[0]["historical_evidence"]["historical_effectiveness"] > 0
    assert "Historical Successful Transition" in matched[0]["inference_sources"]
    if matched[0]["constraint_validation"]["recipe_rules"]:
        assert "Recipe Constraint" in matched[0]["inference_sources"]
        assert matched[0]["explanation"]["recipe_attribution"]


def test_outcome_evaluation_and_effectiveness(client) -> None:
    forecast = create_forecast(client)
    created = client.post(
        "/interventions/recommendations",
        json={"forecast_id": forecast["forecast_id"], "max_results": 1},
    ).json()[0]
    pending = client.post(
        f"/interventions/recommendations/{created['recommendation_id']}/outcome",
        json={"observations": created["intervention_trajectory"]},
    )
    assert pending.status_code == 400
    assert "accepted or applied" in pending.json()["error"]["message"]
    accepted = client.post(
        f"/interventions/recommendations/{created['recommendation_id']}/decisions",
        json={"operator_action": "accepted", "reason": "Approved for outcome validation"},
    )
    assert accepted.status_code == 201
    outcome = client.post(
        f"/interventions/recommendations/{created['recommendation_id']}/outcome",
        json={"observations": created["intervention_trajectory"]},
    )
    assert outcome.status_code == 201, outcome.text
    metrics = outcome.json()["metrics"]
    assert metrics["prediction_accuracy"] == 1
    effectiveness = client.get("/interventions/effectiveness")
    assert effectiveness.status_code == 200
    assert effectiveness.json()["evaluated_count"] >= 1


def test_outcome_rejects_ineligible_recommendation_states(client) -> None:
    forecast = create_forecast(client)
    for state, decision in (
        ("proposed", None),
        ("rejected", {"operator_action": "rejected", "reason": "Not suitable"}),
        (
            "delayed",
            {
                "operator_action": "delayed",
                "reason": "Awaiting process confirmation",
                "delay_duration_seconds": 300,
            },
        ),
    ):
        created = client.post(
            "/interventions/recommendations",
            json={"forecast_id": forecast["forecast_id"], "max_results": 1},
        ).json()[0]
        if decision:
            response = client.post(
                f"/interventions/recommendations/{created['recommendation_id']}/decisions",
                json=decision,
            )
            assert response.status_code == 201
        outcome = client.post(
            f"/interventions/recommendations/{created['recommendation_id']}/outcome",
            json={"observations": created["intervention_trajectory"]},
        )
        assert outcome.status_code == 400
        assert f"current state is {state}" in outcome.json()["error"]["message"]


def test_relationship_filtering_and_ranking(client) -> None:
    response = client.get("/relationships/discovery?method=nonlinear&min_strength=0.1&limit=4")
    assert response.status_code == 200
    rows = response.json()["relationships"]
    assert len(rows) <= 4
    assert all(row["relationship_type"] == "nonlinear" for row in rows)
    assert all(row["impact_direction"] in {"Positive", "Negative"} for row in rows)
    assert all(row["severity"] in {"High", "Medium", "Low"} for row in rows)
    assert all("Basis Weight" in row["summary"] for row in rows)
    assert rows == sorted(rows, key=lambda row: row["strength"], reverse=True)


def test_recommendation_websocket_event_envelope() -> None:
    class Client:
        def __init__(self) -> None:
            self.payload = None

        async def send_json(self, payload) -> None:
            self.payload = payload

    manager = ConnectionManager()
    socket = Client()
    manager.clients.add(socket)
    asyncio.run(manager.broadcast("recommendation_created", {"recommendation_id": "test"}))
    assert socket.payload["event"] == "recommendation_created"
    assert socket.payload["data"]["recommendation_id"] == "test"
