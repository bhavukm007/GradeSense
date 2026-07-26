import pandas as pd
from sklearn.feature_selection import mutual_info_regression


class SequentialRelationshipService:
    @staticmethod
    def _correlation(first: pd.Series, second: pd.Series) -> float:
        paired = pd.concat([first, second], axis=1).dropna()
        if len(paired) < 2 or paired.iloc[:, 0].nunique() < 2 or paired.iloc[:, 1].nunique() < 2:
            return 0.0
        return float(paired.iloc[:, 0].corr(paired.iloc[:, 1]))

    def discover(
        self,
        frame: pd.DataFrame,
        max_lag: int = 12,
        grade_pair: str | None = None,
        stage: str | None = None,
        method: str | None = None,
        min_strength: float = 0,
        limit: int = 30,
    ) -> dict:
        data = frame.copy()
        if grade_pair:
            current, target = grade_pair.split("->", maxsplit=1)
            data = data[(data["current_grade"] == current) & (data["target_grade"] == target)]
        if stage:
            ranges = {
                "early": (0.0, 0.33),
                "middle": (0.33, 0.67),
                "late": (0.67, 1.01),
            }
            lower, upper = ranges[stage]
            data = data[
                (data["transition_progress"] >= lower) & (data["transition_progress"] < upper)
            ]
        variables = [
            "stock_flow",
            "filler_flow",
            "steam_pressure",
            "machine_speed",
            "dryer_temperature",
            "moisture",
            "ash",
            "caliper",
            "reel_tension",
        ]
        relationships = []
        for variable in variables:
            best = {"lag": 0, "correlation": 0.0}
            rolling_values = []
            for _transition_id, group in data.groupby("transition_id", sort=False):
                ordered = group.sort_values("timestep")
                rolling_values.append(
                    self._correlation(
                        ordered[variable].rolling(5, min_periods=2).mean(),
                        ordered["basis_weight"],
                    )
                )
                for lag in range(max_lag + 1):
                    correlation = self._correlation(
                        ordered[variable].shift(lag),
                        ordered["basis_deviation_pct"],
                    )
                    if abs(correlation) > abs(best["correlation"]):
                        best = {"lag": lag, "correlation": float(correlation)}
            relationships.append(
                {
                    "relationship_type": "lag",
                    "variable": variable,
                    "best_lag": best["lag"],
                    "lag_correlation": round(best["correlation"], 5),
                    "rolling_correlation": round(float(pd.Series(rolling_values).mean()), 5),
                    "grade_pair": grade_pair,
                    "stage": stage,
                    "transition_count": int(data["transition_id"].nunique()),
                }
            )
        clean = data[variables + ["basis_deviation_pct"]].dropna()
        if len(clean) >= 10:
            nonlinear = mutual_info_regression(
                clean[variables], clean["basis_deviation_pct"], random_state=42
            )
            scale = max(float(nonlinear.max()), 1e-12)
            relationships.extend(
                {
                    "relationship_type": "nonlinear",
                    "variable": variable,
                    "strength": round(float(value) / scale, 5),
                    "grade_pair": grade_pair,
                    "stage": stage,
                    "transition_count": int(data["transition_id"].nunique()),
                }
                for variable, value in zip(variables, nonlinear, strict=True)
            )
            top_variables = [
                item[0]
                for item in sorted(
                    zip(variables, nonlinear, strict=True),
                    key=lambda item: item[1],
                    reverse=True,
                )[:5]
            ]
            for first_index, first in enumerate(top_variables):
                for second in top_variables[first_index + 1 :]:
                    interaction = clean[first] * clean[second]
                    strength = abs(self._correlation(interaction, clean["basis_deviation_pct"]))
                    relationships.append(
                        {
                            "relationship_type": "interaction",
                            "variable": first,
                            "interacts_with": second,
                            "strength": round(float(strength), 5),
                            "grade_pair": grade_pair,
                            "stage": stage,
                            "transition_count": int(data["transition_id"].nunique()),
                        }
                    )
        for item in relationships:
            item["strength"] = item.get("strength", abs(item.get("lag_correlation", 0)))
        relationships = [
            item
            for item in relationships
            if (method is None or item["relationship_type"] == method)
            and item["strength"] >= min_strength
        ]
        relationships.sort(key=lambda item: item["strength"], reverse=True)
        relationships = relationships[:limit]
        return {
            "relationships": relationships,
            "method": (
                "transition-grouped lagged Pearson, mutual information, and "
                "pairwise feature interaction"
            ),
            "max_lag": max_lag,
            "record_count": len(data),
        }
