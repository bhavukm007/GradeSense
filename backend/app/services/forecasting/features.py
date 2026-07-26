from collections.abc import Sequence

import numpy as np
import pandas as pd

SENSOR_FEATURES = [
    "stock_flow",
    "filler_flow",
    "steam_pressure",
    "machine_speed",
    "dryer_temperature",
    "moisture",
    "ash",
    "caliper",
    "basis_weight",
    "reel_tension",
    "transition_progress",
]
GRADE_INDEX = {
    "Newsprint": 0,
    "CopyPaper": 1,
    "Kraft": 2,
    "Coated": 3,
    "Board": 4,
}


class TemporalFeatureEngineer:
    """Single source of truth for training and online temporal features."""

    def __init__(self, history_window: int) -> None:
        self.history_window = history_window

    def transform(self, history: pd.DataFrame) -> dict[str, float]:
        if len(history) < self.history_window:
            raise ValueError(f"At least {self.history_window} ordered samples are required.")
        window = history.tail(self.history_window).reset_index(drop=True)
        features: dict[str, float] = {}
        lag_steps = sorted(
            lag
            for lag in {0, 1, 2, 5, 10, min(self.history_window - 1, 19)}
            if lag < self.history_window
        )
        for name in SENSOR_FEATURES:
            values = window[name].astype(float)
            for lag in lag_steps:
                features[f"{name}_lag_{lag}"] = float(values.iloc[-1 - lag])
            for size in (5, 10, self.history_window):
                segment = values.tail(min(size, len(values)))
                features[f"{name}_mean_{size}"] = float(segment.mean())
                features[f"{name}_std_{size}"] = float(segment.std(ddof=0))
            features[f"{name}_derivative"] = float(values.iloc[-1] - values.iloc[-2])
            denominator = max(abs(float(values.iloc[-2])), 1e-6)
            features[f"{name}_rate"] = float((values.iloc[-1] - values.iloc[-2]) / denominator)
        latest = window.iloc[-1]
        target = float(latest["target_basis_weight"])
        features["distance_from_target"] = float(latest["basis_weight"] - target)
        features["deviation_from_target_pct"] = float(
            100 * (latest["basis_weight"] - target) / max(target, 1)
        )
        features["transition_elapsed"] = float(latest["timestep"])
        features["time_since_transition_start"] = float(
            latest["timestep"] - window.iloc[0]["timestep"]
        )
        features["target_basis_weight"] = target
        features["current_grade_code"] = float(GRADE_INDEX.get(str(latest["current_grade"]), -1))
        features["target_grade_code"] = float(GRADE_INDEX.get(str(latest["target_grade"]), -1))
        features["grade_pair_code"] = float(
            features["current_grade_code"] * 10 + features["target_grade_code"]
        )
        return features

    @staticmethod
    def columns(features: Sequence[dict[str, float]]) -> list[str]:
        if not features:
            return []
        return sorted(features[0])

    def vector(self, history: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
        features = self.transform(history)
        return np.asarray([[features[column] for column in columns]], dtype=float)
