"""SQLAlchemy model registry.

Domain models will be imported here as they are introduced in later phases so
Alembic can discover them through the shared metadata.
"""

from app.models.intelligence import (
    AlertHistory,
    ForecastCrossingEvent,
    ForecastHistory,
    InterventionSimulation,
    ModelMetadata,
    OperatorFeedback,
    PredictionHistory,
    RecommendationHistory,
    RollingMetricSnapshot,
    StreamingSession,
)

__all__ = [
    "AlertHistory",
    "ForecastCrossingEvent",
    "ForecastHistory",
    "InterventionSimulation",
    "ModelMetadata",
    "OperatorFeedback",
    "PredictionHistory",
    "RecommendationHistory",
    "RollingMetricSnapshot",
    "StreamingSession",
]
