from datetime import UTC, datetime
from threading import RLock
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.models.intelligence import (
    AuditLog,
    ForecastHistory,
    RecommendationDecision,
    RecommendationOutcome,
)
from app.schemas.forecasting import ForecastRequest, SequencePoint
from app.schemas.intelligence import ProcessInput
from app.services.forecasting.service import ForecastingService
from app.services.intelligence import IntelligenceService
from app.services.intervention import InterventionEngine, OutcomeEvaluator


class DemoSeedService:
    """Populate a judge-ready workflow using existing inference and lifecycle services."""

    _seed_lock = RLock()

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def seed(self, session: Session) -> dict[str, int]:
        with self._seed_lock:
            existing = self._existing_seed(session)
            return existing if existing is not None else self._seed_once(session)

    @staticmethod
    def _existing_seed(session: Session) -> dict[str, int] | None:
        audit = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == "demo_outcome_seeded")
            .order_by(AuditLog.timestamp.desc())
            .limit(1)
        )
        if audit is None or session.get(ForecastHistory, UUID(audit.entity_id)) is None:
            return None
        keys = (
            "predictions",
            "forecasts",
            "recommendations",
            "decisions",
            "outcomes",
            "audit_records",
        )
        if not all(key in audit.details for key in keys):
            return None
        return {key: int(audit.details[key]) for key in keys}

    def _seed_once(self, session: Session) -> dict[str, int]:
        predictions = self._seed_predictions(session)
        forecast_row, recommendations = self._seed_forecast_recommendations(session)
        decisions = 0
        outcomes = 0
        actions = ("accepted", "rejected", "applied")
        for recommendation, action in zip(recommendations, actions, strict=False):
            recommendation.state = action
            session.add(
                RecommendationDecision(
                    recommendation_id=recommendation.id,
                    operator_action=action,
                    reason="Honeywell judge demo seed",
                    notes="Seeded through Demo Mode using the existing lifecycle.",
                )
            )
            decisions += 1
            if action == "accepted":
                metrics = OutcomeEvaluator().evaluate(
                    recommendation,
                    [
                        type(
                            "Observation",
                            (),
                            {"basis_weight": point["basis_weight"]},
                        )()
                        for point in recommendation.intervention_trajectory
                    ],
                )
                session.add(
                    RecommendationOutcome(
                        recommendation_id=recommendation.id,
                        observations=recommendation.intervention_trajectory,
                        metrics=metrics,
                    )
                )
                recommendation.state = "evaluated"
                outcomes += 1
        audit_actions = (
            ("demo_predictions_seeded", "prediction"),
            ("demo_forecast_seeded", "forecast"),
            ("demo_recommendations_seeded", "recommendation"),
            ("demo_decisions_seeded", "recommendation_decision"),
            ("demo_outcome_seeded", "recommendation_outcome"),
        )
        result = {
            "predictions": predictions,
            "forecasts": 1,
            "recommendations": len(recommendations),
            "decisions": decisions,
            "outcomes": outcomes,
            "audit_records": len(audit_actions),
        }
        for action, entity in audit_actions:
            session.add(
                AuditLog(
                    timestamp=datetime.now(UTC),
                    actor="demo-mode",
                    action=action,
                    entity=entity,
                    entity_id=str(forecast_row.id),
                    details={
                        **result,
                        "model_retrained": False,
                        "dataset_regenerated": False,
                    },
                    request_id=None,
                )
            )
        session.commit()
        return result

    def _seed_predictions(self, session: Session) -> int:
        frame = pd.read_csv(self.settings.dataset_path).head(3)
        service = IntelligenceService(self.settings, session)
        for _, row in frame.iterrows():
            service.predict(
                ProcessInput.model_validate(
                    {field: row[field] for field in ProcessInput.model_fields}
                )
            )
        return len(frame)

    def _seed_forecast_recommendations(self, session: Session) -> tuple[ForecastHistory, list]:
        frame = pd.read_csv(self.settings.sequential_dataset_path)
        forecasting = ForecastingService(self.settings)
        history_window = int(forecasting.artifacts.load()["history_window"])
        for transition_id, group in frame.groupby("transition_id", sort=False):
            ordered = group.sort_values("timestep")
            if len(ordered) < history_window:
                continue
            request = ForecastRequest.model_validate(
                {
                    "transition_id": f"DEMO-{transition_id}",
                    "current_grade": ordered.iloc[0]["current_grade"],
                    "target_grade": ordered.iloc[0]["target_grade"],
                    "target_basis_weight": ordered.iloc[0]["target_basis_weight"],
                    "history": [
                        {field: row[field] for field in SequencePoint.model_fields}
                        for _, row in ordered.head(history_window).iterrows()
                    ],
                    "forecast_horizon": min(self.settings.forecast_horizon, 12),
                }
            )
            result = forecasting.forecast(request)
            row = ForecastHistory(
                id=result.forecast_id,
                transition_id=result.transition_id,
                model_version=result.model_version,
                request_data=request.model_dump(mode="json"),
                trajectory=[point.model_dump(mode="json") for point in result.trajectory],
                specification=result.specification.model_dump(mode="json"),
                confidence=result.confidence,
                explanation=result.explanation,
                top_influencing_variables=[list(item) for item in result.top_influencing_variables],
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            recommendations = InterventionEngine(forecasting).generate(
                session, row, max_results=5, max_variables=2
            )
            if len(recommendations) >= 3:
                return row, recommendations
        raise RuntimeError("Demo Mode could not find a transition with three improving actions.")
