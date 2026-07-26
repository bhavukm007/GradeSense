from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.domain.features import PROCESS_RANGES
from app.schemas.intelligence import Recommendation
from app.services.model import ModelService, PredictionResult


@dataclass(frozen=True)
class Intervention:
    variable: str
    candidate: Callable[[float], float]
    verb: str
    unit: str


INTERVENTIONS = [
    Intervention("steam_pressure", lambda value: value + 0.35, "Increase", "bar"),
    Intervention("steam_pressure", lambda value: value - 0.35, "Reduce", "bar"),
    Intervention("machine_speed", lambda value: value - 40, "Reduce", "m/min"),
    Intervention("dryer_temperature", lambda value: value + 4, "Increase", "°C"),
    Intervention("dryer_temperature", lambda value: value - 4, "Reduce", "°C"),
    Intervention("pulp_consistency", lambda value: value + 0.2, "Increase", "%"),
    Intervention("pulp_consistency", lambda value: value - 0.2, "Reduce", "%"),
    Intervention("reel_tension", lambda value: value - 0.3, "Reduce", "kN/m"),
    Intervention("refining_energy", lambda value: value + 10, "Increase", "kWh/t"),
    Intervention("headbox_pressure", lambda value: value - 0.2, "Reduce", "bar"),
]


class RecommendationService:
    def __init__(self, model_service: ModelService) -> None:
        self.model_service = model_service

    def recommend(self, values: dict[str, Any], baseline: PredictionResult) -> list[Recommendation]:
        evaluated: list[tuple[float, Intervention, float, PredictionResult]] = []
        for intervention in INTERVENTIONS:
            current = float(values[intervention.variable])
            lower, upper = PROCESS_RANGES[intervention.variable]
            candidate = min(max(intervention.candidate(current), lower), upper)
            if candidate == current:
                continue
            adjusted = dict(values)
            adjusted[intervention.variable] = candidate
            predicted = self.model_service.predict(adjusted)
            risk_improvement = baseline.off_spec_probability - predicted.off_spec_probability
            quality_improvement = predicted.quality_score - baseline.quality_score
            stabilization_improvement = baseline.stabilization_time - predicted.stabilization_time
            score = (
                risk_improvement
                + max(quality_improvement, 0) / 200
                + max(stabilization_improvement, 0) / 300
            )
            evaluated.append((score, intervention, candidate, predicted))

        evaluated.sort(key=lambda item: item[0], reverse=True)
        recommendations: list[Recommendation] = []
        used_variables: set[str] = set()
        for score, intervention, candidate, predicted in evaluated:
            if intervention.variable in used_variables or score <= 0:
                continue
            risk_points = max(
                (baseline.off_spec_probability - predicted.off_spec_probability) * 100,
                0,
            )
            quality_gain = max(predicted.quality_score - baseline.quality_score, 0)
            stabilization_gain = max(baseline.stabilization_time - predicted.stabilization_time, 0)
            expected_improvement = risk_points + quality_gain + stabilization_gain / 3
            if expected_improvement < 0.001:
                continue
            confidence = min(
                0.98,
                0.5 + min(abs(score) * 4, 0.3) + abs(baseline.off_spec_probability - 0.5) * 0.2,
            )
            recommendations.append(
                Recommendation(
                    text=(
                        f"{intervention.verb} {intervention.variable.replace('_', ' ')} "
                        f"to {candidate:.2f} {intervention.unit}."
                    ),
                    confidence=round(confidence, 4),
                    expected_improvement=round(expected_improvement, 3),
                    affected_variables=[intervention.variable],
                    inference_sources=["Forecast", "Correlation Analysis"],
                )
            )
            used_variables.add(intervention.variable)
            if len(recommendations) == 4:
                break
        return recommendations
