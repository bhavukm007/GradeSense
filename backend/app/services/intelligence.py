from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.domain.features import TARGET_FEATURES
from app.models.intelligence import PredictionHistory, RecommendationHistory
from app.schemas.intelligence import (
    CorrelationPair,
    CorrelationResponse,
    DatasetRegenerateResponse,
    DatasetStatisticsResponse,
    ModelInfoResponse,
    PaginationMeta,
    PredictionHistoryItem,
    PredictionHistoryResponse,
    PredictionResponse,
    ProcessInput,
    RecommendationHistoryItem,
    RecommendationHistoryResponse,
    RecommendationResponse,
)
from app.services.dataset import SyntheticDatasetGenerator
from app.services.explainability import ExplainabilityService
from app.services.model import ModelService
from app.services.recommendation import RecommendationService


class IntelligenceService:
    _training_lock = RLock()
    _dataset_lock = RLock()
    _dataset_cache: tuple[Path, int, pd.DataFrame] | None = None
    _statistics_cache: tuple[Path, int, DatasetStatisticsResponse] | None = None

    def __init__(self, settings: Settings, session: Session) -> None:
        self.settings = settings
        self.session = session
        self.dataset_generator = SyntheticDatasetGenerator()
        self.model_service = ModelService(settings)
        self.explainability_service = ExplainabilityService(self.model_service)
        self.recommendation_service = RecommendationService(self.model_service)

    def ensure_ready(self) -> None:
        if self.settings.model_path.exists() and self.settings.dataset_path.exists():
            self.model_service.latest_metadata(self.session)
            return
        missing = [
            str(path)
            for path in (self.settings.dataset_path, self.settings.model_path)
            if not path.exists()
        ]
        raise RuntimeError(
            "Required intelligence artifacts are unavailable; startup will not generate "
            f"or retrain them. Missing: {', '.join(missing)}"
        )

    def regenerate(self, records: int, seed: int) -> DatasetRegenerateResponse:
        with self._training_lock:
            frame = self.dataset_generator.generate(records, seed)
            self.dataset_generator.save(frame, self.settings.dataset_path)
            metadata = self.model_service.train(frame, self.session)
        return DatasetRegenerateResponse(
            records=len(frame),
            dataset_path=str(self.settings.dataset_path),
            model_version=metadata.version,
            training_metrics=metadata.metrics,
        )

    def predict(
        self, process_input: ProcessInput, persist_history: bool = True
    ) -> PredictionResponse:
        values = process_input.model_dump()
        prediction = self.model_service.predict(values)
        explanation = self.explainability_service.explain(values, prediction)
        artifact = self.model_service.load()
        history = PredictionHistory(
            id=uuid4(),
            model_version=artifact["version"],
            input_data=values,
            quality_score=prediction.quality_score,
            off_spec_probability=prediction.off_spec_probability,
            stabilization_time=prediction.stabilization_time,
            explanation=explanation.model_dump(mode="json"),
        )
        if persist_history:
            self.session.add(history)
            self.session.commit()
            self.session.refresh(history)
        return PredictionResponse(
            prediction_id=history.id,
            quality_score=round(prediction.quality_score, 3),
            off_spec_probability=round(prediction.off_spec_probability, 5),
            expected_stabilization_time=round(prediction.stabilization_time, 3),
            model_version=artifact["version"],
            explanation=explanation,
            created_at=self._as_utc(history.created_at or datetime.now(UTC)),
        )

    def recommend(
        self, process_input: ProcessInput, persist_history: bool = True
    ) -> RecommendationResponse:
        prediction_response = self.predict(process_input, persist_history=persist_history)
        baseline = self.model_service.predict(process_input.model_dump())
        recommendations = self.recommendation_service.recommend(
            process_input.model_dump(), baseline
        )
        history = RecommendationHistory(
            id=uuid4(),
            prediction_id=prediction_response.prediction_id,
            recommendations=[
                recommendation.model_dump(mode="json") for recommendation in recommendations
            ],
        )
        if persist_history:
            self.session.add(history)
            self.session.commit()
            self.session.refresh(history)
        return RecommendationResponse(
            recommendation_id=history.id,
            prediction=prediction_response,
            recommendations=recommendations,
            created_at=self._as_utc(history.created_at or datetime.now(UTC)),
        )

    def correlations(self, limit: int = 10) -> CorrelationResponse:
        frame = self._load_dataset()
        numeric = frame.select_dtypes(include="number")
        matrix = numeric.corr()
        pairs = [
            CorrelationPair(
                first_variable=first,
                second_variable=second,
                correlation=round(float(matrix.loc[first, second]), 5),
            )
            for index, first in enumerate(matrix.columns)
            for second in matrix.columns[index + 1 :]
        ]
        positive = sorted(
            (pair for pair in pairs if pair.correlation > 0),
            key=lambda pair: pair.correlation,
            reverse=True,
        )[:limit]
        negative = sorted(
            (pair for pair in pairs if pair.correlation < 0),
            key=lambda pair: pair.correlation,
        )[:limit]
        return CorrelationResponse(
            record_count=len(frame),
            correlation_matrix={
                column: {
                    row: round(float(value), 5) for row, value in matrix[column].to_dict().items()
                }
                for column in matrix.columns
            },
            strongest_positive_correlations=positive,
            strongest_negative_correlations=negative,
        )

    def dataset_statistics(self) -> DatasetStatisticsResponse:
        path = self.settings.dataset_path.resolve()
        modified_ns = path.stat().st_mtime_ns
        with self._dataset_lock:
            cached = type(self)._statistics_cache
            if cached is not None and cached[:2] == (path, modified_ns):
                return cached[2]
        frame = self._load_dataset()
        numeric = frame.select_dtypes(include="number")
        descriptions = numeric.describe().loc[["mean", "50%", "std", "min", "max"]]
        response = DatasetStatisticsResponse(
            record_count=len(frame),
            generated_at=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
            columns=list(frame.columns),
            missing_values={column: int(value) for column, value in frame.isna().sum().items()},
            numeric_summary={
                column: {
                    statistic: round(float(descriptions.loc[statistic, column]), 5)
                    for statistic in descriptions.index
                }
                for column in descriptions.columns
            },
            grade_distribution={
                str(grade): int(count)
                for grade, count in frame["target_grade"].value_counts().items()
            },
        )
        with self._dataset_lock:
            type(self)._statistics_cache = (path, modified_ns, response)
        return response

    def model_info(self) -> ModelInfoResponse:
        metadata = self.model_service.latest_metadata(self.session)
        return ModelInfoResponse(
            model_type=metadata.model_type,
            model_version=metadata.version,
            trained_at=self._as_utc(metadata.trained_at),
            training_records=metadata.training_records,
            feature_count=metadata.feature_count,
            target_metrics=metadata.metrics,
            dataset_checksum=metadata.dataset_checksum,
            supported_outputs=TARGET_FEATURES,
            artifact_path=metadata.artifact_path,
        )

    def prediction_history(self, page: int, page_size: int) -> PredictionHistoryResponse:
        total = self.session.scalar(select(func.count(PredictionHistory.id))) or 0
        rows = self.session.scalars(
            select(PredictionHistory)
            .order_by(PredictionHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return PredictionHistoryResponse(
            items=[
                PredictionHistoryItem(
                    prediction_id=row.id,
                    model_version=row.model_version,
                    input_data=ProcessInput.model_validate(row.input_data),
                    quality_score=row.quality_score,
                    off_spec_probability=row.off_spec_probability,
                    expected_stabilization_time=row.stabilization_time,
                    explanation=row.explanation,
                    created_at=self._as_utc(row.created_at),
                )
                for row in rows
            ],
            pagination=self._pagination(page, page_size, total),
        )

    def recommendation_history(self, page: int, page_size: int) -> RecommendationHistoryResponse:
        total = self.session.scalar(select(func.count(RecommendationHistory.id))) or 0
        rows = self.session.scalars(
            select(RecommendationHistory)
            .order_by(RecommendationHistory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return RecommendationHistoryResponse(
            items=[
                RecommendationHistoryItem(
                    recommendation_id=row.id,
                    prediction_id=row.prediction_id,
                    recommendations=row.recommendations,
                    created_at=self._as_utc(row.created_at),
                )
                for row in rows
            ],
            pagination=self._pagination(page, page_size, total),
        )

    def _load_dataset(self) -> pd.DataFrame:
        path = Path(self.settings.dataset_path).resolve()
        if not path.exists():
            raise FileNotFoundError("The generated dataset is not available.")
        modified_ns = path.stat().st_mtime_ns
        with self._dataset_lock:
            cached = type(self)._dataset_cache
            if cached is not None and cached[:2] == (path, modified_ns):
                return cached[2]
            frame = pd.read_csv(path)
            type(self)._dataset_cache = (path, modified_ns, frame)
            return frame

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _pagination(page: int, page_size: int, total: int) -> PaginationMeta:
        return PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, (total + page_size - 1) // page_size),
        )
