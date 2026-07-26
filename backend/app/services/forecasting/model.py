from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, roc_auc_score

from app.services.forecasting.windowing import ForecastWindows


@dataclass(frozen=True)
class ForecastModelResult:
    median: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    crossing_probability: float


class ForecastArtifactService:
    """Versioned direct multi-horizon gradient-boosting model provider."""

    _artifacts: dict[Path, dict[str, Any]] = {}
    _lock = RLock()

    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path = artifact_path
        self._artifact: dict[str, Any] | None = None

    def train(
        self,
        windows: ForecastWindows,
        history_window: int,
        forecast_horizon: int,
        stride: int,
        random_state: int = 42,
    ) -> dict[str, Any]:
        unique_transitions = np.unique(windows.transition_ids)
        rng = np.random.default_rng(random_state)
        rng.shuffle(unique_transitions)
        split = max(1, int(len(unique_transitions) * 0.8))
        train_ids = set(unique_transitions[:split])
        train_mask = np.asarray(
            [transition_id in train_ids for transition_id in windows.transition_ids]
        )
        validation_mask = ~train_mask
        x_train = windows.features.loc[train_mask]
        x_validation = windows.features.loc[validation_mask]
        y_train = windows.targets[train_mask]
        y_validation = windows.targets[validation_mask]
        models: list[HistGradientBoostingRegressor] = []
        residual_intervals: list[float] = []
        horizon_mae: list[float] = []
        for horizon_index in range(forecast_horizon):
            model = HistGradientBoostingRegressor(
                learning_rate=0.07,
                max_iter=170,
                max_leaf_nodes=24,
                l2_regularization=0.2,
                random_state=random_state,
            )
            model.fit(x_train, y_train[:, horizon_index])
            validation_prediction = model.predict(x_validation)
            residuals = np.abs(y_validation[:, horizon_index] - validation_prediction)
            models.append(model)
            residual_intervals.append(float(np.quantile(residuals, 0.9)))
            horizon_mae.append(
                float(mean_absolute_error(y_validation[:, horizon_index], validation_prediction))
            )
        classifier = GradientBoostingClassifier(random_state=random_state)
        classifier.fit(x_train, windows.crossing[train_mask])
        crossing_probabilities = classifier.predict_proba(x_validation)[:, 1]
        crossing_auc = (
            float(roc_auc_score(windows.crossing[validation_mask], crossing_probabilities))
            if len(np.unique(windows.crossing[validation_mask])) > 1
            else 0.5
        )
        importance = permutation_importance(
            models[0],
            x_validation,
            y_validation[:, 0],
            n_repeats=3,
            random_state=random_state,
        )
        feature_importance = {
            feature: float(max(value, 0))
            for feature, value in zip(
                windows.features.columns, importance.importances_mean, strict=True
            )
        }
        total = sum(feature_importance.values()) or 1.0
        feature_importance = {
            key: value / total
            for key, value in sorted(
                feature_importance.items(), key=lambda item: item[1], reverse=True
            )
        }
        trained_at = datetime.now(UTC)
        artifact = {
            "version": f"hgb-forecast-{trained_at:%Y%m%d%H%M%S}",
            "trained_at": trained_at,
            "history_window": history_window,
            "forecast_horizon": forecast_horizon,
            "stride": stride,
            "feature_columns": list(windows.features.columns),
            "trajectory_models": models,
            "crossing_classifier": classifier,
            "residual_intervals": residual_intervals,
            "feature_importance": feature_importance,
            "metrics": {
                "mean_trajectory_mae": float(np.mean(horizon_mae)),
                "crossing_roc_auc": crossing_auc,
                "horizon_mae": horizon_mae,
                "training_windows": int(train_mask.sum()),
                "validation_windows": int(validation_mask.sum()),
                "training_transitions": len(train_ids),
                "validation_transitions": len(unique_transitions) - len(train_ids),
            },
        }
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, self.artifact_path)
        self._artifact = artifact
        with self._lock:
            self._artifacts[self.artifact_path.resolve()] = artifact
        return artifact

    def load(self) -> dict[str, Any]:
        if self._artifact is None:
            if not self.artifact_path.exists():
                raise FileNotFoundError(
                    "The sequential forecast artifact is not available. "
                    "Run the explicit forecast training command."
                )
            resolved = self.artifact_path.resolve()
            with self._lock:
                if resolved not in self._artifacts:
                    self._artifacts[resolved] = joblib.load(resolved)
                self._artifact = self._artifacts[resolved]
        return self._artifact

    def predict(self, features: pd.DataFrame, horizon: int | None = None) -> ForecastModelResult:
        artifact = self.load()
        supported = int(artifact["forecast_horizon"])
        selected_horizon = min(horizon or supported, supported)
        median = np.asarray(
            [
                model.predict(features)[0]
                for model in artifact["trajectory_models"][:selected_horizon]
            ],
            dtype=float,
        )
        intervals = np.asarray(artifact["residual_intervals"][:selected_horizon], dtype=float)
        probability = float(artifact["crossing_classifier"].predict_proba(features)[0, 1])
        return ForecastModelResult(
            median=median,
            lower=median - intervals,
            upper=median + intervals,
            crossing_probability=probability,
        )
