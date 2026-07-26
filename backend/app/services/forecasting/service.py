from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import numpy as np
import pandas as pd

from app.config.settings import Settings
from app.schemas.forecasting import (
    ForecastRequest,
    ForecastResponse,
    ForecastSimulationResponse,
    InterventionChange,
    SpecificationStatus,
    TrajectoryPoint,
)
from app.services.forecasting.features import SENSOR_FEATURES, TemporalFeatureEngineer
from app.services.forecasting.model import ForecastArtifactService, ForecastModelResult


class ForecastingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        from app.services.registry import active_model_path

        self.artifacts = ForecastArtifactService(
            active_model_path("forecast", settings.forecast_model_path.resolve())
        )

    def forecast(
        self, request: ForecastRequest, forecast_id: UUID | None = None
    ) -> ForecastResponse:
        artifact = self.artifacts.load()
        history_window = int(artifact["history_window"])
        frame = self._history_frame(request)
        engineer = TemporalFeatureEngineer(history_window)
        feature_values = engineer.transform(frame)
        columns = artifact["feature_columns"]
        features = pd.DataFrame([[feature_values[column] for column in columns]], columns=columns)
        result = self.artifacts.predict(features, request.forecast_horizon)
        return self._response(request, result, artifact, feature_values, forecast_id or uuid4())

    def simulate(
        self,
        request: ForecastRequest,
        baseline: ForecastResponse,
        changes: list[InterventionChange],
        simulation_id: UUID | None = None,
        recommendation_id: UUID | None = None,
    ) -> ForecastSimulationResponse:
        intervention_request = request.model_copy(deep=True)
        point = intervention_request.history[-1]
        for change in changes:
            setattr(point, change.variable, change.value)
        intervention = self.forecast(intervention_request)
        baseline_spec = baseline.specification
        intervention_spec = intervention.specification
        baseline_peak = abs(baseline_spec.maximum_predicted_deviation_pct)
        intervention_peak = abs(intervention_spec.maximum_predicted_deviation_pct)
        baseline_stabilization = baseline_spec.predicted_stabilization_step
        intervention_stabilization = intervention_spec.predicted_stabilization_step
        stabilization_improvement = (
            max(baseline_stabilization - intervention_stabilization, 0)
            if baseline_stabilization is not None and intervention_stabilization is not None
            else 0
        )
        baseline_crossing = baseline_spec.predicted_crossing_step
        intervention_crossing = intervention_spec.predicted_crossing_step
        crossing_avoided = baseline_crossing is not None and intervention_crossing is None
        crossing_delay = (
            intervention_crossing - baseline_crossing
            if baseline_crossing is not None and intervention_crossing is not None
            else None
        )
        risk_reduction = max(
            baseline_spec.crossing_probability - intervention_spec.crossing_probability,
            0,
        )
        deviation_reduction = max(baseline_peak - intervention_peak, 0)
        change_text = ", ".join(
            f"{change.variable.replace('_', ' ')} to {change.value:.2f}" for change in changes
        )
        explanation = (
            f"Simulating {change_text} changes the maximum predicted deviation "
            f"from {baseline_peak:.2f}% to {intervention_peak:.2f}% and crossing "
            f"probability from {baseline_spec.crossing_probability:.1%} to "
            f"{intervention_spec.crossing_probability:.1%}."
        )
        return ForecastSimulationResponse(
            simulation_id=simulation_id or uuid4(),
            forecast_id=baseline.forecast_id,
            recommendation_id=recommendation_id or uuid4(),
            changes=changes,
            baseline_trajectory=baseline.trajectory,
            intervention_trajectory=intervention.trajectory,
            baseline_crossing_probability=baseline_spec.crossing_probability,
            intervention_crossing_probability=intervention_spec.crossing_probability,
            risk_reduction=risk_reduction,
            expected_deviation_reduction=deviation_reduction,
            expected_stabilization_improvement=stabilization_improvement,
            crossing_delay_steps=crossing_delay,
            crossing_avoided=crossing_avoided,
            confidence=min(baseline.confidence, intervention.confidence),
            explanation=explanation,
            created_at=datetime.now(UTC),
        )

    def _response(
        self,
        request: ForecastRequest,
        result: ForecastModelResult,
        artifact: dict,
        feature_values: dict[str, float],
        forecast_id: UUID,
    ) -> ForecastResponse:
        latest = request.history[-1]
        sample_delta = (
            request.history[-1].timestamp - request.history[-2].timestamp
            if len(request.history) > 1
            else timedelta(seconds=self.settings.forecast_sample_seconds)
        )
        target = request.target_basis_weight
        lower_spec = target * 0.975
        upper_spec = target * 1.025
        trajectory: list[TrajectoryPoint] = []
        crossing_step: int | None = None
        crossing_time: datetime | None = None
        maximum_deviation = 0.0
        for index, (median, lower, upper) in enumerate(
            zip(result.median, result.lower, result.upper, strict=True), start=1
        ):
            deviation = 100 * (median - target) / max(target, 1)
            maximum_deviation = (
                deviation if abs(deviation) > abs(maximum_deviation) else maximum_deviation
            )
            timestamp = latest.timestamp + sample_delta * index
            if crossing_step is None and abs(deviation) > 2.5:
                crossing_step = index
                crossing_time = timestamp
            trajectory.append(
                TrajectoryPoint(
                    step=index,
                    timestamp=timestamp,
                    basis_weight=float(median),
                    lower_bound=float(lower),
                    upper_bound=float(upper),
                    deviation_pct=float(deviation),
                    lower_spec_limit=lower_spec,
                    upper_spec_limit=upper_spec,
                )
            )
        stabilization_step = self._stabilization_step(result.median, target)
        interval_width = float(np.mean(result.upper - result.lower))
        confidence = max(0.0, min(1.0, 1 - interval_width / max(target * 0.1, 1)))
        raw_importance = artifact["feature_importance"]
        influence_by_source: dict[str, float] = {}
        for feature, importance in raw_importance.items():
            source = next(
                (sensor for sensor in SENSOR_FEATURES if feature.startswith(sensor)),
                feature,
            )
            influence_by_source[source] = influence_by_source.get(source, 0.0) + float(importance)
        top = sorted(influence_by_source.items(), key=lambda item: item[1], reverse=True)[:7]
        influential = ", ".join(name.replace("_", " ") for name, _ in top[:3])
        explanation = (
            f"The forecast is driven primarily by {influential}. "
            f"The current basis-weight deviation is "
            f"{feature_values['deviation_from_target_pct']:.2f}%, and the model "
            f"estimates a {result.crossing_probability:.1%} probability of a "
            f"±2.5% specification crossing within the horizon."
        )
        return ForecastResponse(
            forecast_id=forecast_id,
            transition_id=request.transition_id,
            model_version=artifact["version"],
            history_window=int(artifact["history_window"]),
            forecast_horizon=len(trajectory),
            confidence=confidence,
            trajectory=trajectory,
            specification=SpecificationStatus(
                target_basis_weight=target,
                lower_spec_limit=lower_spec,
                upper_spec_limit=upper_spec,
                current_deviation_pct=float(100 * (latest.basis_weight - target) / max(target, 1)),
                maximum_predicted_deviation_pct=maximum_deviation,
                crossing_probability=result.crossing_probability,
                predicted_crossing_step=crossing_step,
                predicted_crossing_time=crossing_time,
                remaining_safe_operating_seconds=(
                    sample_delta.total_seconds() * crossing_step
                    if crossing_step is not None
                    else None
                ),
                predicted_stabilization_step=stabilization_step,
            ),
            top_influencing_variables=top,
            explanation=explanation,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _history_frame(request: ForecastRequest) -> pd.DataFrame:
        rows = []
        for point in request.history:
            rows.append(
                {
                    **point.model_dump(mode="python"),
                    "transition_id": request.transition_id,
                    "current_grade": request.current_grade,
                    "target_grade": request.target_grade,
                    "target_basis_weight": request.target_basis_weight,
                }
            )
        return pd.DataFrame(rows).sort_values("timestep")

    @staticmethod
    def _stabilization_step(trajectory: np.ndarray, target: float) -> int | None:
        deviations = np.abs(100 * (trajectory - target) / max(target, 1))
        for index in range(len(deviations) - 2):
            if np.all(deviations[index : index + 3] <= 1.0):
                return index + 1
        return None
