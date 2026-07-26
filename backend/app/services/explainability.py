from typing import Any

from app.domain.features import PROCESS_FEATURES
from app.schemas.intelligence import Explanation, FeatureContribution
from app.services.model import ModelService, PredictionResult

DISPLAY_NAMES = {
    "machine_speed": "machine speed",
    "steam_pressure": "steam pressure",
    "dryer_temperature": "dryer temperature",
    "moisture": "moisture",
    "basis_weight": "basis weight",
    "caliper": "caliper",
    "pulp_consistency": "pulp consistency",
    "stock_flow": "stock flow",
    "refining_energy": "refining energy",
    "headbox_pressure": "headbox pressure",
    "reel_tension": "reel tension",
    "ambient_temperature": "ambient temperature",
    "humidity": "ambient humidity",
    "current_grade": "current grade",
    "target_grade": "target grade",
}


class ExplainabilityService:
    """Local counterfactual attribution backed by the persisted prediction model."""

    def __init__(self, model_service: ModelService) -> None:
        self.model_service = model_service

    def explain(self, values: dict[str, Any], prediction: PredictionResult) -> Explanation:
        artifact = self.model_service.load()
        baselines = artifact["baselines"]
        global_importance = artifact["feature_importance"]
        contributions: list[FeatureContribution] = []
        for feature in PROCESS_FEATURES:
            counterfactual = dict(values)
            counterfactual[feature] = baselines[feature]
            baseline_prediction = self.model_service.predict(counterfactual)
            contribution = (
                prediction.off_spec_probability - baseline_prediction.off_spec_probability
            )
            contributions.append(
                FeatureContribution(
                    feature=feature,
                    value=values[feature],
                    contribution=round(contribution, 5),
                    importance=global_importance[feature],
                    direction="increases risk" if contribution >= 0 else "reduces risk",
                )
            )
        contributions.sort(
            key=lambda item: abs(item.contribution) * (0.5 + item.importance),
            reverse=True,
        )
        top = contributions[:5]
        summary = self._summary(top, prediction)
        return Explanation(
            summary=summary,
            top_contributing_features=top,
            feature_importance=global_importance,
        )

    @staticmethod
    def _summary(contributions: list[FeatureContribution], prediction: PredictionResult) -> str:
        risk_features = [item for item in contributions if item.contribution > 0]
        protective_features = [item for item in contributions if item.contribution <= 0]
        if risk_features:
            names = " and ".join(DISPLAY_NAMES[item.feature] for item in risk_features[:2])
            return (
                f"{names.capitalize()} are the strongest contributors to the "
                f"{prediction.off_spec_probability:.1%} predicted off-spec risk."
            )
        names = " and ".join(DISPLAY_NAMES[item.feature] for item in protective_features[:2])
        return (
            f"{names.capitalize()} currently reduce off-spec risk; the predicted probability is "
            f"{prediction.off_spec_probability:.1%}."
        )
