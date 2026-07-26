PROCESS_FEATURES = [
    "current_grade",
    "target_grade",
    "machine_speed",
    "steam_pressure",
    "dryer_temperature",
    "moisture",
    "basis_weight",
    "caliper",
    "pulp_consistency",
    "stock_flow",
    "refining_energy",
    "headbox_pressure",
    "reel_tension",
    "ambient_temperature",
    "humidity",
]

CATEGORICAL_FEATURES = ["current_grade", "target_grade"]
NUMERIC_FEATURES = [feature for feature in PROCESS_FEATURES if feature not in CATEGORICAL_FEATURES]
TARGET_FEATURES = ["quality_score", "off_spec_probability", "stabilization_time"]

PROCESS_RANGES: dict[str, tuple[float, float]] = {
    "machine_speed": (350.0, 1_200.0),
    "steam_pressure": (3.0, 9.5),
    "dryer_temperature": (80.0, 145.0),
    "moisture": (2.5, 10.0),
    "basis_weight": (40.0, 220.0),
    "caliper": (45.0, 300.0),
    "pulp_consistency": (2.2, 5.5),
    "stock_flow": (1_200.0, 5_500.0),
    "refining_energy": (80.0, 260.0),
    "headbox_pressure": (1.5, 5.5),
    "reel_tension": (1.0, 6.5),
    "ambient_temperature": (12.0, 42.0),
    "humidity": (20.0, 95.0),
}
