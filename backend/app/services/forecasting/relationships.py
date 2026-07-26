import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_regression


class SequentialRelationshipService:
    @staticmethod
    def _correlation(first: pd.Series, second: pd.Series) -> float:
        first_values = first.to_numpy(dtype=float, copy=False)
        second_values = second.to_numpy(dtype=float, copy=False)
        valid = np.isfinite(first_values) & np.isfinite(second_values)
        first_values = first_values[valid]
        second_values = second_values[valid]
        if (
            len(first_values) < 2
            or np.ptp(first_values) == 0
            or np.ptp(second_values) == 0
        ):
            return 0.0
        return float(np.corrcoef(first_values, second_values)[0, 1])

    @staticmethod
    def _group_correlations(
        group_ids: pd.Series,
        first: pd.Series,
        second: pd.Series,
    ) -> pd.Series:
        values = pd.DataFrame(
            {
                "group": group_ids,
                "first": first,
                "second": second,
            }
        ).dropna()
        values["first_squared"] = values["first"] ** 2
        values["second_squared"] = values["second"] ** 2
        values["product"] = values["first"] * values["second"]
        totals = values.groupby("group", sort=False).agg(
            count=("first", "count"),
            first_sum=("first", "sum"),
            second_sum=("second", "sum"),
            first_squared_sum=("first_squared", "sum"),
            second_squared_sum=("second_squared", "sum"),
            product_sum=("product", "sum"),
        )
        numerator = (
            totals["count"] * totals["product_sum"]
            - totals["first_sum"] * totals["second_sum"]
        )
        denominator = np.sqrt(
            (
                totals["count"] * totals["first_squared_sum"]
                - totals["first_sum"] ** 2
            )
            * (
                totals["count"] * totals["second_squared_sum"]
                - totals["second_sum"] ** 2
            )
        )
        return (numerator / denominator).where(
            (totals["count"] >= 2) & (denominator > 0),
            0.0,
        )

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
        data = data.sort_values(["transition_id", "timestep"])
        grouped = data.groupby("transition_id", sort=False)
        relationships = []
        for variable in variables:
            best = {"lag": 0, "correlation": 0.0}
            rolling = grouped[variable].transform(
                lambda values: values.rolling(5, min_periods=2).mean()
            )
            rolling_correlations = self._group_correlations(
                data["transition_id"],
                rolling,
                data["basis_weight"],
            )
            for lag in range(max_lag + 1):
                lag_correlations = self._group_correlations(
                    data["transition_id"],
                    grouped[variable].shift(lag),
                    data["basis_deviation_pct"],
                )
                if lag_correlations.empty:
                    continue
                strongest = lag_correlations.abs().idxmax()
                correlation = float(lag_correlations.loc[strongest])
                if abs(correlation) > abs(best["correlation"]):
                    best = {"lag": lag, "correlation": correlation}
            relationships.append(
                {
                    "relationship_type": "lag",
                    "variable": variable,
                    "best_lag": best["lag"],
                    "lag_correlation": round(best["correlation"], 5),
                    "rolling_correlation": round(float(rolling_correlations.mean()), 5),
                    "grade_pair": grade_pair,
                    "stage": stage,
                    "transition_count": int(data["transition_id"].nunique()),
                    "impact_direction": ("Positive" if best["correlation"] >= 0 else "Negative"),
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
                    "impact_direction": (
                        "Positive"
                        if self._correlation(clean[variable], clean["basis_deviation_pct"]) >= 0
                        else "Negative"
                    ),
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
                    signed_strength = self._correlation(interaction, clean["basis_deviation_pct"])
                    relationships.append(
                        {
                            "relationship_type": "interaction",
                            "variable": first,
                            "interacts_with": second,
                            "strength": round(abs(float(signed_strength)), 5),
                            "grade_pair": grade_pair,
                            "stage": stage,
                            "transition_count": int(data["transition_id"].nunique()),
                            "impact_direction": (
                                "Positive" if signed_strength >= 0 else "Negative"
                            ),
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
        for item in relationships:
            strength = float(item["strength"])
            item["severity"] = "High" if strength >= 0.7 else "Medium" if strength >= 0.4 else "Low"
            stage_text = f" during {stage} transition" if stage else ""
            if item["relationship_type"] == "lag":
                item["summary"] = (
                    f"{item['variable'].replace('_', ' ').title()} leads Basis Weight by "
                    f"approximately {item['best_lag']} timesteps{stage_text}."
                )
            elif item["relationship_type"] == "interaction":
                item["summary"] = (
                    f"{item['variable'].replace('_', ' ').title()} interacting with "
                    f"{item['interacts_with'].replace('_', ' ')} has a "
                    f"{item['impact_direction'].lower()} impact on Basis Weight{stage_text}."
                )
            else:
                item["summary"] = (
                    f"{item['variable'].replace('_', ' ').title()} has a nonlinear "
                    f"{item['impact_direction'].lower()} relationship with Basis Weight"
                    f"{stage_text}."
                )
        return {
            "relationships": relationships,
            "method": (
                "transition-grouped lagged Pearson, mutual information, and "
                "pairwise feature interaction"
            ),
            "max_lag": max_lag,
            "record_count": len(data),
        }
