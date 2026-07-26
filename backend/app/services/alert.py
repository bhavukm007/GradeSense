from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.intelligence import AlertHistory
from app.schemas.intelligence import PredictionResponse, ProcessInput
from app.schemas.realtime import AlertResponse


class AlertService:
    def evaluate(
        self,
        session: Session,
        sample: ProcessInput,
        prediction: PredictionResponse,
        previous: ProcessInput | None = None,
    ) -> list[AlertResponse]:
        candidates: list[tuple[str, str, str, list[str], str]] = []
        if prediction.off_spec_probability >= 0.55:
            candidates.append(
                (
                    "critical",
                    "High off-spec risk",
                    f"Predicted off-spec probability is {prediction.off_spec_probability:.1%}.",
                    ["off_spec_probability"],
                    "Review current recommendations before continuing the transition.",
                )
            )
        if prediction.quality_score < 65:
            candidates.append(
                (
                    "critical",
                    "Very low predicted quality",
                    f"Quality score fell to {prediction.quality_score:.1f}.",
                    ["quality_score"],
                    "Slow the transition and verify sheet quality immediately.",
                )
            )
        if sample.moisture < 4 or sample.moisture > 8:
            candidates.append(
                (
                    "warning",
                    "Abnormal moisture",
                    f"Moisture is {sample.moisture:.2f}%, outside the preferred transition band.",
                    ["moisture"],
                    "Inspect drying balance and stock conditions.",
                )
            )
        if sample.steam_pressure < 4.2 or sample.steam_pressure > 8.3:
            candidates.append(
                (
                    "warning",
                    "Steam pressure deviation",
                    f"Steam pressure is {sample.steam_pressure:.2f} bar.",
                    ["steam_pressure"],
                    "Verify steam header and dryer demand.",
                )
            )
        if sample.dryer_temperature < 92 or sample.dryer_temperature > 137:
            candidates.append(
                (
                    "warning",
                    "Dryer temperature deviation",
                    f"Dryer temperature is {sample.dryer_temperature:.1f} °C.",
                    ["dryer_temperature"],
                    "Check dryer section controls and steam balance.",
                )
            )
        if prediction.expected_stabilization_time > 80:
            candidates.append(
                (
                    "warning",
                    "Long stabilization predicted",
                    "Expected stabilization time is "
                    f"{prediction.expected_stabilization_time:.1f} minutes.",
                    ["stabilization_time"],
                    "Hold conservative setpoints until quality stabilizes.",
                )
            )
        if previous and (
            abs(sample.machine_speed - previous.machine_speed) > 120
            or abs(sample.moisture - previous.moisture) > 1.5
            or abs(sample.steam_pressure - previous.steam_pressure) > 1.2
        ):
            candidates.append(
                (
                    "critical",
                    "Rapid process drift",
                    "Multiple process values changed faster than the expected "
                    "transition trajectory.",
                    ["machine_speed", "moisture", "steam_pressure"],
                    "Pause aggressive setpoint changes and verify sensor integrity.",
                )
            )
        alerts = []
        for severity, title, description, variables, action in candidates:
            row = AlertHistory(
                severity=severity,
                title=title,
                description=description,
                affected_variables=variables,
                suggested_action=action,
                acknowledged=False,
                prediction_id=prediction.prediction_id,
            )
            session.add(row)
            session.flush()
            alerts.append(
                AlertResponse(
                    id=row.id,
                    severity=severity,
                    title=title,
                    description=description,
                    timestamp=datetime.now(UTC),
                    affected_variables=variables,
                    suggested_action=action,
                    acknowledged=False,
                    prediction_id=prediction.prediction_id,
                )
            )
        if candidates:
            session.commit()
        return alerts
