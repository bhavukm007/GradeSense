from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.services.forecasting.features import TemporalFeatureEngineer


@dataclass(frozen=True)
class ForecastWindows:
    features: pd.DataFrame
    targets: np.ndarray
    crossing: np.ndarray
    transition_ids: np.ndarray


class TransitionWindowBuilder:
    def __init__(self, history_window: int, forecast_horizon: int, stride: int) -> None:
        self.history_window = history_window
        self.forecast_horizon = forecast_horizon
        self.stride = stride
        self.engineer = TemporalFeatureEngineer(history_window)

    def build(self, frame: pd.DataFrame) -> ForecastWindows:
        feature_rows: list[dict[str, float]] = []
        target_rows: list[np.ndarray] = []
        crossing_rows: list[bool] = []
        transition_ids: list[str] = []
        for transition_id, group in frame.groupby("transition_id", sort=False):
            ordered = group.sort_values("timestep").reset_index(drop=True)
            maximum = len(ordered) - self.forecast_horizon
            for end in range(self.history_window - 1, maximum, self.stride):
                history = ordered.iloc[end - self.history_window + 1 : end + 1]
                future = ordered.iloc[end + 1 : end + 1 + self.forecast_horizon]
                feature_rows.append(self.engineer.transform(history))
                targets = future["basis_weight"].to_numpy(dtype=float)
                target_rows.append(targets)
                target_basis = float(history.iloc[-1]["target_basis_weight"])
                deviations = 100 * (targets - target_basis) / max(target_basis, 1)
                crossing_rows.append(bool(np.any(np.abs(deviations) > 2.5)))
                transition_ids.append(str(transition_id))
        return ForecastWindows(
            features=pd.DataFrame(feature_rows).sort_index(axis=1),
            targets=np.vstack(target_rows),
            crossing=np.asarray(crossing_rows, dtype=int),
            transition_ids=np.asarray(transition_ids),
        )
