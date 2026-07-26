import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["GRADESENSE_ENVIRONMENT"] = "test"
os.environ["GRADESENSE_DATABASE_URL"] = "sqlite:///./tests/.artifacts/test.db"
os.environ["GRADESENSE_DATASET_PATH"] = "./tests/.artifacts/test_dataset.csv"
os.environ["GRADESENSE_MODEL_PATH"] = "./tests/.artifacts/test_model.joblib"
os.environ["GRADESENSE_DATASET_RECORDS"] = "1500"
os.environ["GRADESENSE_MODEL_ESTIMATORS"] = "30"
os.environ["GRADESENSE_SEQUENTIAL_DATASET_PATH"] = "./tests/.artifacts/test_sequences.csv"
os.environ["GRADESENSE_FORECAST_MODEL_PATH"] = "./tests/.artifacts/test_forecast.joblib"
os.environ["GRADESENSE_FORECAST_HISTORY_WINDOW"] = "10"
os.environ["GRADESENSE_FORECAST_HORIZON"] = "6"
os.environ["GRADESENSE_FORECAST_WINDOW_STRIDE"] = "5"

artifact_directory = Path("tests/.artifacts")
artifact_directory.mkdir(parents=True, exist_ok=True)
for artifact_name in (
    "test.db",
    "test_dataset.csv",
    "test_model.joblib",
    "test_sequences.csv",
    "test_forecast.joblib",
):
    (artifact_directory / artifact_name).unlink(missing_ok=True)

from app.config.settings import get_settings  # noqa: E402
from app.database.session import SessionFactory, initialize_database  # noqa: E402
from app.main import app  # noqa: E402
from app.services.dataset import SyntheticDatasetGenerator  # noqa: E402
from app.services.forecasting.model import ForecastArtifactService  # noqa: E402
from app.services.forecasting.windowing import TransitionWindowBuilder  # noqa: E402
from app.services.model import ModelService  # noqa: E402
from app.services.sequential_dataset import (  # noqa: E402
    SequentialDatasetConfig,
    SequentialTransitionGenerator,
)

settings = get_settings()
initialize_database()
snapshot_generator = SyntheticDatasetGenerator()
snapshot_frame = snapshot_generator.generate(settings.dataset_records, settings.dataset_seed)
snapshot_generator.save(snapshot_frame, settings.dataset_path)
with SessionFactory() as session:
    ModelService(settings).train(snapshot_frame, session)
generator = SequentialTransitionGenerator()
sequence_frame = generator.generate(
    SequentialDatasetConfig(transitions=24, steps_per_transition=70, seed=73)
)
generator.save(sequence_frame, settings.sequential_dataset_path)
forecast_windows = TransitionWindowBuilder(10, 6, 5).build(sequence_frame)
ForecastArtifactService(settings.forecast_model_path).train(forecast_windows, 10, 6, 5)


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
