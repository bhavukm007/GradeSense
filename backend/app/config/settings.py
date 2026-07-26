from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GRADESENSE_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GradeSenseAI API"
    app_version: str = "0.2.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = "sqlite:///./gradesense.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    dataset_path: Path = Path("../data/generated/paper_mill_transitions.csv")
    model_path: Path = Path("../models/grade_transition_model.joblib")
    dataset_records: int = Field(default=20_000, ge=1_000)
    dataset_seed: int = 42
    model_estimators: int = Field(default=160, ge=20)
    model_random_state: int = 42
    stream_interval_seconds: float = Field(default=2.0, ge=0.05, le=60)
    sequential_dataset_path: Path = Path("../data/sequential/paper_mill_transition_sequences.csv")
    forecast_model_path: Path = Path("../models/basis_weight_forecast.joblib")
    forecast_history_window: int = Field(default=20, ge=5, le=120)
    forecast_horizon: int = Field(default=12, ge=1, le=120)
    forecast_window_stride: int = Field(default=4, ge=1, le=60)
    forecast_sample_seconds: int = Field(default=10, ge=1, le=300)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
