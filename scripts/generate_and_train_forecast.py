"""Explicitly build Phase 05 sequential data and its dedicated forecast artifact.

This command never reads from or writes to the legacy snapshot dataset/model.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.chdir(PROJECT_ROOT / "backend")

from app.config.settings import get_settings  # noqa: E402
from app.services.forecasting.model import ForecastArtifactService  # noqa: E402
from app.services.forecasting.windowing import TransitionWindowBuilder  # noqa: E402
from app.services.sequential_dataset import (  # noqa: E402
    SequentialDatasetConfig,
    SequentialTransitionGenerator,
)


def main() -> None:
    settings = get_settings()
    generator = SequentialTransitionGenerator()
    frame = generator.generate(SequentialDatasetConfig())
    generator.save(frame, settings.sequential_dataset_path)
    windows = TransitionWindowBuilder(
        settings.forecast_history_window,
        settings.forecast_horizon,
        settings.forecast_window_stride,
    ).build(frame)
    artifact = ForecastArtifactService(settings.forecast_model_path).train(
        windows,
        settings.forecast_history_window,
        settings.forecast_horizon,
        settings.forecast_window_stride,
    )
    print(f"Sequential rows: {len(frame):,}")
    print(f"Forecast windows: {len(windows.features):,}")
    print(f"Artifact: {settings.forecast_model_path}")
    print(f"Metrics: {artifact['metrics']}")


if __name__ == "__main__":
    main()
