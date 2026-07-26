import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import joblib
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.domain.features import PROCESS_FEATURES
from app.models.intelligence import RegisteredModel
from app.schemas.administration import ModelRegister


class ModelValidationError(ValueError):
    pass


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def schema_checksum(features: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(features, separators=(",", ":"), sort_keys=False).encode()
    ).hexdigest()


class ModelRegistryService:
    REQUIRED_COMMON = {"version", "trained_at", "metrics"}

    def validate(self, payload: ModelRegister) -> dict[str, Any]:
        path = Path(payload.artifact_path).resolve()
        if not path.is_file():
            raise ModelValidationError("Model artifact does not exist.")
        if file_checksum(path) != payload.artifact_checksum:
            raise ModelValidationError("Artifact checksum does not match.")
        artifact = joblib.load(path)
        missing = self.REQUIRED_COMMON - artifact.keys()
        if missing:
            raise ModelValidationError(
                f"Artifact metadata is incomplete: {', '.join(sorted(missing))}."
            )
        if str(artifact["version"]) != payload.version:
            raise ModelValidationError("Registered version does not match artifact metadata.")
        if not payload.metrics:
            raise ModelValidationError("Validation metrics are required.")
        if payload.model_kind == "prediction":
            required = {"pipeline", "baselines", "feature_importance"}
            expected_schema = schema_checksum(PROCESS_FEATURES)
            pipeline = artifact.get("pipeline")
            if pipeline is None or not hasattr(pipeline, "predict"):
                raise ModelValidationError("Prediction pipeline is incompatible.")
        else:
            required = {
                "feature_columns",
                "trajectory_models",
                "crossing_classifier",
                "residual_intervals",
                "history_window",
                "forecast_horizon",
            }
            expected_schema = schema_checksum(list(artifact.get("feature_columns", [])))
            if not artifact.get("trajectory_models") or not hasattr(
                artifact.get("crossing_classifier"), "predict_proba"
            ):
                raise ModelValidationError("Forecast pipeline is incompatible.")
        missing = required - artifact.keys()
        if missing:
            raise ModelValidationError(
                f"Artifact pipeline is incomplete: {', '.join(sorted(missing))}."
            )
        if payload.feature_schema_checksum != expected_schema:
            raise ModelValidationError("Feature schema checksum is incompatible.")
        return artifact

    def register(self, session: Session, payload: ModelRegister) -> RegisteredModel:
        exists = session.scalar(
            select(RegisteredModel).where(
                RegisteredModel.model_kind == payload.model_kind,
                RegisteredModel.version == payload.version,
            )
        )
        if exists:
            raise ModelValidationError("This model version is already registered.")
        self.validate(payload)
        if payload.status == "active":
            self._archive_active(session, payload.model_kind)
        row = RegisteredModel(**payload.model_dump())
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def promote(self, session: Session, model_id: UUID) -> RegisteredModel:
        row = session.get(RegisteredModel, model_id)
        if row is None:
            raise ModelValidationError("Model not found.")
        self.validate(
            ModelRegister(
                version=row.version,
                name=row.name,
                model_kind=row.model_kind,
                algorithm=row.algorithm,
                trained_at=row.trained_at,
                dataset_checksum=row.dataset_checksum,
                feature_schema_checksum=row.feature_schema_checksum,
                artifact_checksum=row.artifact_checksum,
                artifact_path=row.artifact_path,
                metrics=row.metrics,
                training_parameters=row.training_parameters,
                description=row.description,
                status="active",
            )
        )
        self._archive_active(session, row.model_kind)
        row.status = "active"
        session.commit()
        session.refresh(row)
        return row

    def archive(self, session: Session, model_id: UUID) -> RegisteredModel:
        row = session.get(RegisteredModel, model_id)
        if row is None:
            raise ModelValidationError("Model not found.")
        if row.status == "active":
            raise ModelValidationError("Promote a replacement before archiving the active model.")
        row.status = "archived"
        session.commit()
        session.refresh(row)
        return row

    @staticmethod
    def _archive_active(session: Session, kind: str) -> None:
        for active in session.scalars(
            select(RegisteredModel).where(
                RegisteredModel.model_kind == kind,
                RegisteredModel.status == "active",
            )
        ):
            active.status = "archived"

    def bootstrap_existing(self, session: Session, settings: Settings) -> None:
        for kind, path in (
            ("prediction", settings.model_path.resolve()),
            ("forecast", settings.forecast_model_path.resolve()),
        ):
            if not path.is_file():
                continue
            if session.scalar(select(RegisteredModel).where(RegisteredModel.model_kind == kind)):
                continue
            artifact = joblib.load(path)
            features = (
                PROCESS_FEATURES if kind == "prediction" else list(artifact["feature_columns"])
            )
            row = RegisteredModel(
                version=str(artifact["version"]),
                name=(
                    "Grade transition predictor"
                    if kind == "prediction"
                    else "Basis Weight forecaster"
                ),
                model_kind=kind,
                algorithm=(
                    type(artifact["pipeline"].named_steps["model"]).__name__
                    if kind == "prediction"
                    else type(artifact["trajectory_models"][0]).__name__
                ),
                trained_at=artifact["trained_at"],
                dataset_checksum=str(
                    artifact.get("dataset_checksum")
                    or (
                        file_checksum(settings.sequential_dataset_path.resolve())
                        if settings.sequential_dataset_path.is_file()
                        else "dataset-not-mounted"
                    )
                ),
                feature_schema_checksum=schema_checksum(features),
                artifact_checksum=file_checksum(path),
                artifact_path=str(path),
                metrics=artifact["metrics"],
                training_parameters={
                    key: artifact[key]
                    for key in ("history_window", "forecast_horizon", "stride")
                    if key in artifact
                },
                description="Existing Phase 01–06 artifact registered without modification.",
                status="active",
            )
            session.add(row)
        session.commit()


def active_model_path(kind: str, fallback: Path) -> Path:
    from app.database.session import SessionFactory

    with SessionFactory() as session:
        row = session.scalar(
            select(RegisteredModel).where(
                RegisteredModel.model_kind == kind,
                RegisteredModel.status == "active",
            )
        )
        return Path(row.artifact_path) if row else fallback
