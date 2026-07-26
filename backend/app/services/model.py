import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.domain.features import CATEGORICAL_FEATURES, PROCESS_FEATURES, TARGET_FEATURES
from app.models.intelligence import ModelMetadata
from app.services.preprocessing import build_preprocessor


@dataclass(frozen=True)
class PredictionResult:
    quality_score: float
    off_spec_probability: float
    stabilization_time: float


class ModelNotReadyError(RuntimeError):
    """Raised when inference is requested before a model artifact exists."""


class ModelService:
    _artifact: dict[str, Any] | None = None
    _artifact_path: Path | None = None
    _lock = RLock()

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        from app.services.registry import active_model_path

        self.model_path = active_model_path("prediction", settings.model_path.resolve()).resolve()

    def train(self, frame: pd.DataFrame, session: Session) -> ModelMetadata:
        features = frame[PROCESS_FEATURES]
        targets = frame[TARGET_FEATURES]
        train_features, test_features, train_targets, test_targets = train_test_split(
            features,
            targets,
            test_size=0.2,
            random_state=self.settings.model_random_state,
        )
        pipeline = Pipeline(
            [
                ("preprocessor", build_preprocessor()),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=self.settings.model_estimators,
                        min_samples_leaf=3,
                        max_features=0.8,
                        n_jobs=-1,
                        random_state=self.settings.model_random_state,
                    ),
                ),
            ]
        )
        pipeline.fit(train_features, train_targets)
        predicted = pipeline.predict(test_features)
        metrics: dict[str, float] = {}
        for index, target in enumerate(TARGET_FEATURES):
            metrics[f"{target}_mae"] = round(
                float(mean_absolute_error(test_targets.iloc[:, index], predicted[:, index])),
                4,
            )
            metrics[f"{target}_r2"] = round(
                float(r2_score(test_targets.iloc[:, index], predicted[:, index])), 4
            )

        checksum = self._dataset_checksum(frame)
        trained_at = datetime.now(UTC)
        version = f"rf-{trained_at:%Y%m%d%H%M%S%f}-{checksum[:8]}"
        baselines = {
            feature: (
                str(features[feature].mode(dropna=True).iloc[0])
                if feature in CATEGORICAL_FEATURES
                else float(features[feature].median())
            )
            for feature in PROCESS_FEATURES
        }
        artifact = {
            "pipeline": pipeline,
            "version": version,
            "trained_at": trained_at,
            "training_records": len(frame),
            "metrics": metrics,
            "dataset_checksum": checksum,
            "baselines": baselines,
            "feature_importance": self._aggregate_feature_importance(pipeline),
        }
        model_path = self.settings.model_path.resolve()
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, model_path)
        with self._lock:
            type(self)._artifact = artifact
            type(self)._artifact_path = model_path

        metadata = ModelMetadata(
            version=version,
            model_type="RandomForestRegressor",
            trained_at=trained_at,
            training_records=len(frame),
            feature_count=len(PROCESS_FEATURES),
            metrics=metrics,
            dataset_checksum=checksum,
            artifact_path=str(model_path),
        )
        session.add(metadata)
        session.commit()
        session.refresh(metadata)
        return metadata

    def predict(self, values: dict[str, Any]) -> PredictionResult:
        artifact = self.load()
        prediction = artifact["pipeline"].predict(pd.DataFrame([values]))[0]
        return PredictionResult(
            quality_score=float(np.clip(prediction[0], 0, 100)),
            off_spec_probability=float(np.clip(prediction[1], 0, 1)),
            stabilization_time=float(max(prediction[2], 0)),
        )

    def load(self) -> dict[str, Any]:
        model_path = self.model_path
        with self._lock:
            if self._artifact is None or self._artifact_path != model_path:
                if not model_path.exists():
                    raise ModelNotReadyError(
                        "No trained model is available. Regenerate the dataset to train one."
                    )
                type(self)._artifact = joblib.load(model_path)
                type(self)._artifact_path = model_path
            return self._artifact

    def latest_metadata(self, session: Session) -> ModelMetadata:
        metadata = session.scalar(
            select(ModelMetadata).order_by(ModelMetadata.trained_at.desc()).limit(1)
        )
        if metadata is None:
            artifact = self.load()
            metadata = ModelMetadata(
                version=artifact["version"],
                model_type="RandomForestRegressor",
                trained_at=artifact["trained_at"],
                training_records=artifact["training_records"],
                feature_count=len(PROCESS_FEATURES),
                metrics=artifact["metrics"],
                dataset_checksum=artifact["dataset_checksum"],
                artifact_path=str(self.settings.model_path.resolve()),
            )
            session.add(metadata)
            session.commit()
            session.refresh(metadata)
        return metadata

    @staticmethod
    def _dataset_checksum(frame: pd.DataFrame) -> str:
        hashed = pd.util.hash_pandas_object(frame, index=True).values.tobytes()
        return hashlib.sha256(hashed).hexdigest()

    @staticmethod
    def _aggregate_feature_importance(pipeline: Pipeline) -> dict[str, float]:
        preprocessor = pipeline.named_steps["preprocessor"]
        transformed_names = preprocessor.get_feature_names_out()
        importances = pipeline.named_steps["model"].feature_importances_
        aggregate = {feature: 0.0 for feature in PROCESS_FEATURES}
        for transformed_name, importance in zip(transformed_names, importances, strict=True):
            source = next(
                (
                    feature
                    for feature in CATEGORICAL_FEATURES
                    if transformed_name.startswith(f"{feature}_")
                ),
                transformed_name,
            )
            if source in aggregate:
                aggregate[source] += float(importance)
        total = sum(aggregate.values()) or 1
        return {
            feature: round(importance / total, 6)
            for feature, importance in sorted(
                aggregate.items(), key=lambda item: item[1], reverse=True
            )
        }
