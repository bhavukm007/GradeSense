from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

GRADE_PROFILES = {
    "Newsprint": {"basis": 48.8, "caliper": 72.0, "speed": 1_050.0, "moisture": 7.2},
    "CopyPaper": {"basis": 80.0, "caliper": 103.0, "speed": 820.0, "moisture": 4.8},
    "Kraft": {"basis": 125.0, "caliper": 170.0, "speed": 650.0, "moisture": 6.2},
    "Coated": {"basis": 95.0, "caliper": 88.0, "speed": 720.0, "moisture": 4.2},
    "Board": {"basis": 190.0, "caliper": 265.0, "speed": 460.0, "moisture": 6.8},
}


class SyntheticDatasetGenerator:
    """Causal simulator for paper-machine grade transition observations."""

    def generate(self, records: int, seed: int) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        grades = np.array(list(GRADE_PROFILES))
        current_indices = rng.integers(0, len(grades), records)
        target_offsets = rng.integers(1, len(grades), records)
        current = grades[current_indices]
        target = grades[(current_indices + target_offsets) % len(grades)]

        current_profile = self._profiles(current)
        target_profile = self._profiles(target)
        grade_distance = (
            np.abs(target_profile["basis"] - current_profile["basis"]) / 145
            + np.abs(target_profile["caliper"] - current_profile["caliper"]) / 220
            + np.abs(target_profile["speed"] - current_profile["speed"]) / 700
        ) / 3
        transition_progress = rng.beta(2.2, 2.0, records)
        ambient_temperature = np.clip(rng.normal(27, 6.5, records), 12, 42)
        humidity = np.clip(
            70 - 1.1 * (ambient_temperature - 24) + rng.normal(0, 9, records), 20, 95
        )

        ideal_speed = target_profile["speed"]
        speed_error = rng.normal(0, 45 + 75 * grade_distance, records)
        machine_speed = np.clip(
            current_profile["speed"]
            + transition_progress * (ideal_speed - current_profile["speed"])
            + speed_error,
            350,
            1_200,
        )
        basis_weight = np.clip(
            current_profile["basis"]
            + transition_progress * (target_profile["basis"] - current_profile["basis"])
            + rng.normal(0, 2.2 + 7 * grade_distance, records),
            40,
            220,
        )
        caliper = np.clip(
            current_profile["caliper"]
            + transition_progress * (target_profile["caliper"] - current_profile["caliper"])
            + rng.normal(0, 4 + 12 * grade_distance, records),
            45,
            300,
        )
        stock_flow = np.clip(
            1_350 + 18.5 * basis_weight + 1.25 * machine_speed + rng.normal(0, 150, records),
            1_200,
            5_500,
        )
        pulp_consistency = np.clip(
            2.7 + 0.006 * (basis_weight - 50) + rng.normal(0, 0.24, records), 2.2, 5.5
        )
        refining_energy = np.clip(
            105 + 0.48 * basis_weight + 24 * grade_distance + rng.normal(0, 14, records),
            80,
            260,
        )
        headbox_pressure = np.clip(
            1.55 + machine_speed / 390 + rng.normal(0, 0.18, records), 1.5, 5.5
        )
        steam_pressure = np.clip(
            4.0 + machine_speed / 350 + 0.013 * basis_weight + rng.normal(0, 0.38, records),
            3,
            9.5,
        )
        dryer_temperature = np.clip(
            74 + 5.2 * steam_pressure + 0.024 * machine_speed + rng.normal(0, 4.5, records),
            80,
            145,
        )
        moisture = np.clip(
            target_profile["moisture"]
            + 0.032 * (humidity - 55)
            - 0.052 * (dryer_temperature - 115)
            - 0.18 * (steam_pressure - 6.5)
            + rng.normal(0, 0.48 + 0.7 * grade_distance, records),
            2.5,
            10,
        )
        reel_tension = np.clip(
            1.4 + 0.014 * caliper + 0.001 * machine_speed + rng.normal(0, 0.32, records),
            1,
            6.5,
        )

        basis_error = np.abs(basis_weight - target_profile["basis"]) / np.maximum(
            target_profile["basis"], 1
        )
        caliper_error = np.abs(caliper - target_profile["caliper"]) / np.maximum(
            target_profile["caliper"], 1
        )
        moisture_error = np.abs(moisture - target_profile["moisture"]) / 3
        speed_overrun = np.maximum(machine_speed - ideal_speed, 0) / 300
        drying_shortfall = (
            np.maximum(112 - dryer_temperature, 0) / 35 + np.maximum(5.8 - steam_pressure, 0) / 4
        )
        tension_stress = np.maximum(reel_tension - 4.8, 0) / 2
        process_deviation = (
            0.24 * basis_error
            + 0.18 * caliper_error
            + 0.25 * moisture_error
            + 0.10 * speed_overrun
            + 0.10 * drying_shortfall
            + 0.06 * tension_stress
            + 0.07 * grade_distance
        )
        latent_risk = (
            -2.8 + 8.5 * process_deviation + 1.1 * grade_distance + rng.normal(0, 0.25, records)
        )
        off_spec_probability = np.clip(1 / (1 + np.exp(-latent_risk)), 0.01, 0.99)
        quality_score = np.clip(
            100 - 47 * off_spec_probability - 17 * process_deviation + rng.normal(0, 1.8, records),
            0,
            100,
        )
        transition_time = np.clip(
            18 + 62 * grade_distance + 24 * process_deviation + rng.normal(0, 4, records),
            8,
            150,
        )
        stabilization_time = np.clip(
            transition_time * (0.62 + 0.75 * off_spec_probability) + rng.normal(0, 3, records),
            5,
            180,
        )

        start = datetime(2024, 1, 1, tzinfo=UTC)
        timestamps = [start + timedelta(minutes=5 * index) for index in range(records)]
        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "current_grade": current,
                "target_grade": target,
                "machine_speed": machine_speed,
                "steam_pressure": steam_pressure,
                "dryer_temperature": dryer_temperature,
                "moisture": moisture,
                "basis_weight": basis_weight,
                "caliper": caliper,
                "pulp_consistency": pulp_consistency,
                "stock_flow": stock_flow,
                "refining_energy": refining_energy,
                "headbox_pressure": headbox_pressure,
                "reel_tension": reel_tension,
                "ambient_temperature": ambient_temperature,
                "humidity": humidity,
                "transition_time": transition_time,
                "quality_score": quality_score,
                "off_spec_probability": off_spec_probability,
                "stabilization_time": stabilization_time,
            }
        )
        numeric_columns = frame.select_dtypes(include="number").columns
        frame[numeric_columns] = frame[numeric_columns].round(4)
        return frame

    @staticmethod
    def save(frame: pd.DataFrame, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)

    @staticmethod
    def _profiles(grades: np.ndarray) -> dict[str, np.ndarray]:
        return {
            key: np.array([GRADE_PROFILES[grade][key] for grade in grades], dtype=float)
            for key in ("basis", "caliper", "speed", "moisture")
        }
