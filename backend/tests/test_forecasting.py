import pandas as pd

from app.config.settings import get_settings
from app.schemas.forecasting import SequencePoint
from app.services.forecasting.features import TemporalFeatureEngineer
from app.services.forecasting.windowing import TransitionWindowBuilder


def request_payload() -> dict:
    settings = get_settings()
    frame = pd.read_csv(settings.sequential_dataset_path)
    history = frame[frame["transition_id"] == frame.iloc[0]["transition_id"]].iloc[20:30]
    return {
        "transition_id": str(history.iloc[-1]["transition_id"]),
        "current_grade": str(history.iloc[-1]["current_grade"]),
        "target_grade": str(history.iloc[-1]["target_grade"]),
        "target_basis_weight": float(history.iloc[-1]["target_basis_weight"]),
        "history": [
            {field: row[field] for field in SequencePoint.model_fields}
            for _, row in history.iterrows()
        ],
        "forecast_horizon": 6,
    }


def test_windows_never_cross_transition_boundaries() -> None:
    frame = pd.read_csv(get_settings().sequential_dataset_path)
    windows = TransitionWindowBuilder(10, 6, 5).build(frame)
    assert len(windows.features) == len(windows.targets)
    assert windows.targets.shape[1] == 6
    assert set(windows.transition_ids).issubset(set(frame["transition_id"]))
    assert len(set(windows.crossing)) == 2


def test_temporal_features_include_lags_rates_and_grade_pair() -> None:
    frame = pd.read_csv(get_settings().sequential_dataset_path).iloc[:10]
    features = TemporalFeatureEngineer(10).transform(frame)
    assert "basis_weight_lag_1" in features
    assert "basis_weight_derivative" in features
    assert "stock_flow_mean_10" in features
    assert "grade_pair_code" in features


def test_forecast_persistence_and_simulation_api(client) -> None:
    payload = request_payload()
    response = client.post("/forecast", json=payload)
    assert response.status_code == 200, response.text
    forecast = response.json()
    assert len(forecast["trajectory"]) == 6
    assert forecast["specification"]["upper_spec_limit"] == (payload["target_basis_weight"] * 1.025)
    stored = client.get(f"/forecast/{forecast['forecast_id']}")
    assert stored.status_code == 200
    simulation = client.post(
        "/forecast/simulate",
        json={
            "forecast_id": forecast["forecast_id"],
            "changes": [{"variable": "stock_flow", "value": 3000}],
        },
    )
    assert simulation.status_code == 201, simulation.text
    result = simulation.json()
    assert result["recommendation_id"]
    assert len(result["baseline_trajectory"]) == 6
    assert len(result["intervention_trajectory"]) == 6
    history = client.get("/forecast/history")
    assert history.status_code == 200
    assert history.json()["total"] >= 1


def test_legacy_prediction_api_remains_operational(client) -> None:
    response = client.post(
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
    assert response.status_code == 200
    assert "quality_score" in response.json()
