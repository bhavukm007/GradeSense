from datetime import UTC, datetime

import numpy as np
import pandas as pd

from app.domain.features import NUMERIC_FEATURES
from app.schemas.intelligence import ProcessInput
from app.schemas.realtime import DriftResponse


class DriftService:
    def calculate(
        self,
        recent: list[ProcessInput],
        training: pd.DataFrame,
        prediction_risks: list[float],
    ) -> DriftResponse:
        scores: dict[str, float] = {}
        if len(recent) >= 5:
            frame = pd.DataFrame([item.model_dump() for item in recent])
            for feature in NUMERIC_FEATURES:
                expected = training[feature].dropna().to_numpy()
                actual = frame[feature].dropna().to_numpy()
                edges = np.unique(np.quantile(expected, np.linspace(0, 1, 11)))
                if len(edges) < 3:
                    continue
                expected_hist = np.histogram(expected, bins=edges)[0] / len(expected)
                actual_hist = np.histogram(np.clip(actual, edges[0], edges[-1]), bins=edges)[
                    0
                ] / max(len(actual), 1)
                expected_hist = np.clip(expected_hist, 0.0001, None)
                actual_hist = np.clip(actual_hist, 0.0001, None)
                scores[feature] = round(
                    float(
                        np.sum((actual_hist - expected_hist) * np.log(actual_hist / expected_hist))
                    ),
                    4,
                )
        overall = max(scores.values(), default=0.0)
        drifting = {key: value for key, value in scores.items() if value >= 0.1}
        prediction_drift = float(np.std(prediction_risks[-20:])) if prediction_risks else 0.0
        severity = (
            "critical"
            if overall >= 0.5
            else ("warning" if overall >= 0.25 else "watch" if overall >= 0.1 else "stable")
        )
        action = (
            "Investigate drifting sensors and validate the active model; "
            "retraining requires explicit approval."
            if severity in {"warning", "critical"}
            else "Continue monitoring the incoming process distribution."
        )
        return DriftResponse(
            score=round(overall, 4),
            severity=severity,
            drifting_variables=drifting,
            prediction_drift=round(prediction_drift, 4),
            recommended_action=action,
            calculated_at=datetime.now(UTC),
        )
