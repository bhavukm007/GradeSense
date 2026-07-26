from dataclasses import dataclass

from app.schemas.forecasting import ForecastRequest, InterventionChange
from app.schemas.intervention import ConstraintValidation


@dataclass(frozen=True)
class Limit:
    minimum: float
    maximum: float
    max_change: float


LIMITS = {
    "stock_flow": Limit(1800, 5200, 1000),
    "filler_flow": Limit(0, 600, 80),
    "steam_pressure": Limit(2.5, 9.5, 0.75),
    "machine_speed": Limit(350, 1400, 100),
    "dryer_temperature": Limit(70, 145, 8),
    "reel_tension": Limit(1.5, 9.0, 0.75),
}

GRADE_LIMITS = {
    "Kraft": {"machine_speed": (350, 1050), "reel_tension": (2.0, 8.5)},
    "CopyPaper": {"machine_speed": (500, 1250), "filler_flow": (40, 500)},
    "Newsprint": {"machine_speed": (650, 1400), "dryer_temperature": (80, 135)},
}


class ConstraintEngine:
    def validate(
        self, request: ForecastRequest, changes: list[InterventionChange]
    ) -> ConstraintValidation:
        checks: list[str] = []
        violations: list[str] = []
        current = request.history[-1]
        seen: set[str] = set()
        for change in changes:
            if change.variable in seen:
                violations.append(f"Duplicate setpoint for {change.variable}.")
                continue
            seen.add(change.variable)
            limit = LIMITS[change.variable]
            checks.append(f"{change.variable} equipment range {limit.minimum:g}..{limit.maximum:g}")
            if not limit.minimum <= change.value <= limit.maximum:
                violations.append(f"{change.variable} exceeds equipment limits.")
            old = float(getattr(current, change.variable))
            if abs(change.value - old) > limit.max_change:
                violations.append(
                    f"{change.variable} change exceeds rate limit {limit.max_change:g}."
                )
            grade_limit = GRADE_LIMITS.get(request.target_grade, {}).get(change.variable)
            if grade_limit:
                checks.append(
                    f"{request.target_grade} {change.variable} range "
                    f"{grade_limit[0]:g}..{grade_limit[1]:g}"
                )
                if not grade_limit[0] <= change.value <= grade_limit[1]:
                    violations.append(
                        f"{change.variable} violates {request.target_grade} grade limits."
                    )
        values = {name: float(getattr(current, name)) for name in LIMITS}
        values.update({item.variable: item.value for item in changes})
        checks.append("steam/dryer and speed/stock dependency constraints")
        if values["dryer_temperature"] > 130 and values["steam_pressure"] > 8.5:
            violations.append("High dryer temperature cannot be combined with high steam pressure.")
        if values["machine_speed"] > 1200 and values["stock_flow"] < 2600:
            violations.append("Stock flow is insufficient for the requested machine speed.")
        return ConstraintValidation(feasible=not violations, checks=checks, violations=violations)
