from datetime import UTC, datetime, timedelta
from itertools import combinations, product
from uuid import uuid4

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.intelligence import (
    ForecastHistory,
    ForecastRecommendation,
    RecommendationDecision,
    RecommendationOutcome,
)
from app.schemas.forecasting import ForecastRequest, InterventionChange
from app.schemas.intervention import (
    EffectivenessResponse,
    ForecastRecommendationResponse,
    HistoricalRecommendationEvidence,
    RecommendationExplanation,
    RecommendationMetrics,
)
from app.services.constraints import LIMITS, ConstraintEngine
from app.services.forecasting.service import ForecastingService

logger = get_logger(__name__)


def recommendation_response(row: ForecastRecommendation) -> ForecastRecommendationResponse:
    explanation = dict(row.explanation)
    public_explanation = {
        key: explanation[key]
        for key in (
            "selection_reason",
            "forecast_causes",
            "trajectory_effect",
            "expected_risks",
            "remaining_uncertainty",
            "recipe_attribution",
        )
        if key in explanation
    }
    return ForecastRecommendationResponse(
        recommendation_id=row.id,
        forecast_id=row.forecast_id,
        state=row.state,
        rank=row.rank,
        affected_variables=row.affected_variables,
        current_values=explanation.get("current_values", {}),
        changes=row.changes,
        baseline_trajectory=row.baseline_trajectory,
        intervention_trajectory=row.intervention_trajectory,
        metrics=row.metrics,
        confidence=row.confidence,
        constraint_validation=row.constraint_validation,
        explanation=public_explanation,
        inference_sources=explanation.get("inference_sources", ["Forecast", "Historical Trend"]),
        historical_evidence=explanation.get(
            "historical_evidence",
            {
                "similar_transition_count": 0,
                "historical_acceptance_rate": 0,
                "historical_effectiveness": 0,
            },
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
        expires_at=row.expires_at,
    )


class InterventionEngine:
    def __init__(self, forecasting: ForecastingService) -> None:
        self.forecasting = forecasting
        self.constraints = ConstraintEngine()

    def generate(
        self,
        session: Session | None,
        forecast_row: ForecastHistory,
        max_results: int,
        max_variables: int,
        persist: bool = True,
        attach: bool = True,
    ) -> list[ForecastRecommendation]:
        request = ForecastRequest.model_validate(forecast_row.request_data)
        from app.api.routes.forecasting import response_from_row

        baseline = response_from_row(forecast_row)
        variables = [
            name for name, _importance in baseline.top_influencing_variables if name in LIMITS
        ]
        variables.extend(name for name in LIMITS if name not in variables)
        variables = variables[:5]
        candidates: list[tuple[float, object, object]] = []
        for count in range(1, max_variables + 1):
            for selected in combinations(variables, count):
                choices = []
                for variable in selected:
                    current = float(getattr(request.history[-1], variable))
                    delta = LIMITS[variable].max_change * 0.5
                    choices.append((current - delta, current + delta))
                for values in product(*choices):
                    changes = [
                        InterventionChange(variable=variable, value=value)
                        for variable, value in zip(selected, values, strict=True)
                    ]
                    validation = self.constraints.validate(request, changes)
                    if not validation.feasible:
                        continue
                    simulation = self.forecasting.simulate(request, baseline, changes)
                    before = abs(baseline.specification.maximum_predicted_deviation_pct)
                    after = abs(
                        max(
                            simulation.intervention_trajectory,
                            key=lambda point: abs(point.deviation_pct),
                        ).deviation_pct
                    )
                    before_stabilization = baseline.specification.predicted_stabilization_step
                    intervention_forecast_stabilization = self._stabilization(
                        simulation.intervention_trajectory
                    )
                    risk_gain = simulation.risk_reduction
                    deviation_gain = max(before - after, 0) / 2.5
                    stabilization_gain = simulation.expected_stabilization_improvement / max(
                        baseline.forecast_horizon, 1
                    )
                    score = risk_gain * 0.6 + deviation_gain * 0.3 + stabilization_gain * 0.1
                    if score <= 0:
                        continue
                    metrics = RecommendationMetrics(
                        crossing_probability_before=simulation.baseline_crossing_probability,
                        crossing_probability_after=simulation.intervention_crossing_probability,
                        predicted_peak_deviation_before=before,
                        predicted_peak_deviation_after=after,
                        predicted_stabilization_time_before=before_stabilization,
                        predicted_stabilization_time_after=intervention_forecast_stabilization,
                        estimated_improvement=score,
                        crossing_avoided=simulation.crossing_avoided,
                        crossing_delay_steps=simulation.crossing_delay_steps,
                    )
                    candidates.append((score, simulation, (validation, metrics)))
        candidates.sort(key=lambda item: item[0], reverse=True)
        rows = []
        for rank, (_score, simulation, details) in enumerate(candidates[:max_results], start=1):
            validation, metrics = details
            try:
                historical_evidence = (
                    self._historical_evidence(
                        session,
                        request.current_grade,
                        request.target_grade,
                        [change.variable for change in simulation.changes],
                    )
                    if session is not None
                    else HistoricalRecommendationEvidence(
                        similar_transition_count=0,
                        historical_acceptance_rate=0,
                        historical_effectiveness=0,
                    )
                )
            except Exception:
                # Historical evidence enriches a recommendation but is never
                # required to generate its forecast-derived action.
                logger.exception("recommendation_historical_evidence_unavailable")
                historical_evidence = HistoricalRecommendationEvidence(
                    similar_transition_count=0,
                    historical_acceptance_rate=0,
                    historical_effectiveness=0,
                )
            inference_sources = ["Forecast", "Historical Trend", "Correlation Analysis"]
            if validation.recipe_rules:
                inference_sources.append("Recipe Constraint")
            if historical_evidence.historical_effectiveness > 0:
                inference_sources.append("Historical Successful Transition")
            causes = [
                name.replace("_", " ")
                for name, _importance in baseline.top_influencing_variables[:3]
            ]
            changed = ", ".join(change.variable.replace("_", " ") for change in simulation.changes)
            risks = [
                f"Setpoint movement for {change.variable.replace('_', ' ')} is "
                f"{abs(change.value - float(getattr(request.history[-1], change.variable))):.2f}."
                for change in simulation.changes
            ]
            row = ForecastRecommendation(
                id=uuid4(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                forecast_id=forecast_row.id,
                state="proposed",
                rank=rank,
                affected_variables=[change.variable for change in simulation.changes],
                changes=[change.model_dump(mode="json") for change in simulation.changes],
                baseline_trajectory=[
                    point.model_dump(mode="json") for point in simulation.baseline_trajectory
                ],
                intervention_trajectory=[
                    point.model_dump(mode="json") for point in simulation.intervention_trajectory
                ],
                metrics=metrics.model_dump(mode="json"),
                confidence=simulation.confidence,
                constraint_validation=validation.model_dump(mode="json"),
                explanation={
                    **RecommendationExplanation(
                        selection_reason=(
                            f"Ranked {rank} by forecast-derived crossing-risk (60%), "
                            "peak-deviation (30%), and stabilization (10%) improvement."
                        ),
                        forecast_causes=causes,
                        trajectory_effect=(
                            f"Changing {changed} reduces crossing probability from "
                            f"{metrics.crossing_probability_before:.1%} to "
                            f"{metrics.crossing_probability_after:.1%} and peak deviation from "
                            f"{metrics.predicted_peak_deviation_before:.2f}% to "
                            f"{metrics.predicted_peak_deviation_after:.2f}%."
                        ),
                        expected_risks=risks,
                        remaining_uncertainty=(
                            f"Joint forecast confidence is {simulation.confidence:.1%}; "
                            "uncertainty is represented by the intervention confidence interval."
                        ),
                        recipe_attribution=validation.recipe_rules,
                    ).model_dump(mode="json"),
                    "inference_sources": inference_sources,
                    "historical_evidence": historical_evidence.model_dump(mode="json"),
                    "current_values": {
                        change.variable: float(getattr(request.history[-1], change.variable))
                        for change in simulation.changes
                    },
                },
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
            )
            if attach and session is not None:
                session.add(row)
            rows.append(row)
        if persist:
            if session is None:
                raise RuntimeError("A database session is required for recommendation persistence.")
            session.commit()
            for row in rows:
                session.refresh(row)
        return rows

    @staticmethod
    def _historical_evidence(
        session: Session,
        current_grade: str,
        target_grade: str,
        affected_variables: list[str],
    ) -> HistoricalRecommendationEvidence:
        # Recommendation history is supporting evidence, not a prerequisite for
        # creating a current recommendation.  Keep this bounded on Render Free.
        recommendations = list(
            session.scalars(
                select(ForecastRecommendation)
                .order_by(ForecastRecommendation.created_at.desc())
                .limit(200)
            )
        )
        similar: list[ForecastRecommendation] = []
        affected = set(affected_variables)
        for recommendation in recommendations:
            forecast = session.get(ForecastHistory, recommendation.forecast_id)
            if forecast is None:
                continue
            request = forecast.request_data
            if (
                request.get("current_grade") == current_grade
                and request.get("target_grade") == target_grade
                and affected.intersection(recommendation.affected_variables)
            ):
                similar.append(recommendation)
        if not similar:
            return HistoricalRecommendationEvidence(
                similar_transition_count=0,
                historical_acceptance_rate=0,
                historical_effectiveness=0,
            )
        ids = [item.id for item in similar]
        decisions = list(
            session.scalars(
                select(RecommendationDecision).where(
                    RecommendationDecision.recommendation_id.in_(ids)
                )
            )
        )
        accepted_ids = {
            item.recommendation_id
            for item in decisions
            if item.operator_action in {"accepted", "applied"}
        }
        outcomes = list(
            session.scalars(
                select(RecommendationOutcome).where(
                    RecommendationOutcome.recommendation_id.in_(ids)
                )
            )
        )
        evidence_ids = accepted_ids | {item.recommendation_id for item in outcomes}
        decided_ids = {item.recommendation_id for item in decisions}
        relevant_ids = decided_ids | {item.recommendation_id for item in outcomes}
        effectiveness = (
            sum(float(item.metrics.get("recommendation_accuracy", 0)) for item in outcomes)
            / len(outcomes)
            if outcomes
            else 0
        )
        return HistoricalRecommendationEvidence(
            similar_transition_count=len(evidence_ids),
            historical_acceptance_rate=(
                len(accepted_ids) / len(relevant_ids) if relevant_ids else 0
            ),
            historical_effectiveness=effectiveness,
        )

    @staticmethod
    def _stabilization(trajectory: list) -> int | None:
        deviations = np.array([abs(point.deviation_pct) for point in trajectory])
        for index in range(max(len(deviations) - 2, 0)):
            if np.all(deviations[index : index + 3] <= 1):
                return index + 1
        return None


class OutcomeEvaluator:
    def evaluate(self, recommendation: ForecastRecommendation, observations: list) -> dict:
        predicted = recommendation.intervention_trajectory
        count = min(len(predicted), len(observations))
        errors = [
            abs(float(observations[index].basis_weight) - float(predicted[index]["basis_weight"]))
            for index in range(count)
        ]
        target = float(predicted[0]["lower_spec_limit"] + predicted[0]["upper_spec_limit"]) / 2
        actual_deviations = [
            abs(100 * (float(point.basis_weight) - target) / target) for point in observations
        ]
        actual_crossing = any(value > 2.5 for value in actual_deviations)
        baseline_crossing = recommendation.metrics["crossing_probability_before"] >= 0.5
        actual_stabilization = next(
            (
                index + 1
                for index in range(len(actual_deviations) - 2)
                if max(actual_deviations[index : index + 3]) <= 1
            ),
            None,
        )
        predicted_before = recommendation.metrics["predicted_peak_deviation_before"]
        return {
            "prediction_accuracy": max(0.0, 1 - float(np.mean(errors)) / max(target, 1)),
            "recommendation_accuracy": max(
                0.0,
                1
                - abs(
                    max(actual_deviations)
                    - recommendation.metrics["predicted_peak_deviation_after"]
                )
                / 2.5,
            ),
            "crossing_avoided": bool(baseline_crossing and not actual_crossing),
            "crossing_delayed": bool(
                actual_crossing and recommendation.metrics["crossing_delay_steps"]
            ),
            "stabilization_improvement": float(
                max(
                    (recommendation.metrics["predicted_stabilization_time_before"] or 0)
                    - (actual_stabilization or len(observations)),
                    0,
                )
            ),
            "actual_vs_predicted_deviation": float(
                max(actual_deviations) - recommendation.metrics["predicted_peak_deviation_after"]
            ),
            "deviation_improvement": max(predicted_before - max(actual_deviations), 0),
        }

    def effectiveness(self, session: Session) -> EffectivenessResponse:
        rows = list(session.scalars(select(RecommendationOutcome)))
        if not rows:
            return EffectivenessResponse(
                evaluated_count=0,
                crossing_avoidance_rate=0,
                crossing_delay_rate=0,
                mean_prediction_error=0,
                mean_deviation_improvement=0,
                mean_stabilization_improvement=0,
            )
        metrics = [row.metrics for row in rows]

        def average(key: str) -> float:
            return sum(float(item[key]) for item in metrics) / len(metrics)

        return EffectivenessResponse(
            evaluated_count=len(rows),
            crossing_avoidance_rate=average("crossing_avoided"),
            crossing_delay_rate=average("crossing_delayed"),
            mean_prediction_error=1 - average("prediction_accuracy"),
            mean_deviation_improvement=average("deviation_improvement"),
            mean_stabilization_improvement=average("stabilization_improvement"),
        )
