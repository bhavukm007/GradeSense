from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from app.services.dataset import GRADE_PROFILES


@dataclass(frozen=True)
class SequentialDatasetConfig:
    transitions: int = 240
    steps_per_transition: int = 240
    sample_seconds: int = 10
    seed: int = 42


class SequentialTransitionGenerator:
    """Stateful paper-machine simulator producing coherent grade transitions."""

    def generate(self, config: SequentialDatasetConfig) -> pd.DataFrame:
        rng = np.random.default_rng(config.seed)
        grades = list(GRADE_PROFILES)
        rows: list[dict[str, object]] = []
        start = datetime(2024, 1, 1, tzinfo=UTC)
        for transition_index in range(config.transitions):
            current_grade = grades[transition_index % len(grades)]
            target_grade = grades[
                (transition_index + 1 + transition_index // len(grades)) % len(grades)
            ]
            if target_grade == current_grade:
                target_grade = grades[(grades.index(current_grade) + 1) % len(grades)]
            current = GRADE_PROFILES[current_grade]
            target = GRADE_PROFILES[target_grade]
            state = {
                "stock_flow": 1_250 + 18.5 * current["basis"] + current["speed"],
                "filler_flow": 190 + 1.7 * current["basis"],
                "steam_pressure": 5.0 + current["basis"] / 75,
                "machine_speed": current["speed"],
                "dryer_temperature": 108 + current["basis"] / 18,
                "moisture": current["moisture"],
                "ash": 7.5 + (3.0 if current_grade == "Coated" else 0),
                "caliper": current["caliper"],
                "basis_weight": current["basis"],
                "reel_tension": 1.6 + current["caliper"] * 0.014,
                "pulp_consistency": 3.4,
                "refining_energy": 135 + current["basis"] * 0.24,
                "headbox_pressure": 2.1 + current["speed"] / 620,
                "ambient_temperature": 24.0,
                "humidity": 52.0,
            }
            ar_noise = 0.0
            disturbance_start = int(rng.integers(60, 145))
            disturbance_size = float(rng.normal(0, 0.055))
            for step in range(config.steps_per_transition):
                progress = min(1.0, step / max(config.steps_per_transition * 0.62, 1))
                smooth = progress * progress * (3 - 2 * progress)
                target_speed = current["speed"] + smooth * (target["speed"] - current["speed"])
                target_basis = target["basis"]
                stock_setpoint = 1_250 + 18.5 * target_basis + target_speed
                filler_setpoint = (
                    190 + 1.7 * target_basis + (240 if target_grade == "Coated" else 0)
                )
                steam_setpoint = 5.0 + target_basis / 75 + target_speed / 1_900
                if disturbance_start <= step < disturbance_start + 18:
                    stock_setpoint *= 1 + disturbance_size
                state["machine_speed"] += 0.07 * (target_speed - state["machine_speed"])
                state["stock_flow"] += 0.09 * (stock_setpoint - state["stock_flow"])
                state["filler_flow"] += 0.08 * (filler_setpoint - state["filler_flow"])
                state["steam_pressure"] += 0.12 * (steam_setpoint - state["steam_pressure"])
                desired_temp = 77 + 5.0 * state["steam_pressure"] + 0.022 * state["machine_speed"]
                state["dryer_temperature"] += 0.1 * (desired_temp - state["dryer_temperature"])
                desired_ash = 7.5 + (3.0 if target_grade == "Coated" else 0)
                state["ash"] += 0.06 * (desired_ash - state["ash"])
                desired_moisture = (
                    target["moisture"]
                    - 0.045 * (state["dryer_temperature"] - 115)
                    - 0.12 * (state["steam_pressure"] - 6.2)
                )
                state["moisture"] += 0.08 * (desired_moisture - state["moisture"])
                mass_basis = (
                    state["stock_flow"] - 1_250 - state["machine_speed"]
                ) / 18.5 + 0.008 * (state["filler_flow"] - filler_setpoint)
                ar_noise = 0.82 * ar_noise + float(rng.normal(0, 0.32))
                desired_basis = mass_basis
                state["basis_weight"] += 0.13 * (desired_basis - state["basis_weight"]) + ar_noise
                desired_caliper = target["caliper"] * (state["basis_weight"] / max(target_basis, 1))
                state["caliper"] += 0.09 * (desired_caliper - state["caliper"])
                desired_tension = 1.6 + state["caliper"] * 0.014
                state["reel_tension"] += 0.08 * (desired_tension - state["reel_tension"])
                state["pulp_consistency"] += 0.06 * (
                    3.1 + target_basis / 260 - state["pulp_consistency"]
                )
                state["refining_energy"] += 0.06 * (
                    135 + target_basis * 0.24 - state["refining_energy"]
                )
                state["headbox_pressure"] += 0.09 * (
                    2.1 + state["machine_speed"] / 620 - state["headbox_pressure"]
                )
                state["ambient_temperature"] += float(rng.normal(0, 0.012))
                state["humidity"] += 0.04 * (52 - state["humidity"]) + float(rng.normal(0, 0.04))
                timestamp = start + timedelta(
                    seconds=(transition_index * config.steps_per_transition + step)
                    * config.sample_seconds
                )
                deviation = 100 * (state["basis_weight"] - target_basis) / max(target_basis, 1)
                rows.append(
                    {
                        "transition_id": f"TR-{transition_index + 1:05d}",
                        "timestamp": timestamp.isoformat(),
                        "timestep": step,
                        "current_grade": current_grade,
                        "target_grade": target_grade,
                        "recipe": f"{current_grade}_to_{target_grade}",
                        "transition_progress": progress,
                        "target_basis_weight": target_basis,
                        **{key: round(float(value), 5) for key, value in state.items()},
                        "basis_deviation_pct": round(deviation, 5),
                        "off_spec": abs(deviation) > 2.5,
                    }
                )
        return pd.DataFrame(rows)

    @staticmethod
    def save(frame: pd.DataFrame, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
