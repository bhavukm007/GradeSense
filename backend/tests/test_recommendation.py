from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.schemas.intelligence import ProcessInput
from app.services.model import ModelService
from app.services.recommendation import RecommendationService
from tests.test_intelligence_api import PROCESS_INPUT


def test_recommendation_candidates_improve_model_objective(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    model_service = ModelService(get_settings())
    values = ProcessInput(**PROCESS_INPUT).model_dump()
    baseline = model_service.predict(values)
    recommendations = RecommendationService(model_service).recommend(values, baseline)

    assert recommendations
    assert all(recommendation.confidence >= 0.5 for recommendation in recommendations)
    assert all(recommendation.expected_improvement > 0 for recommendation in recommendations)
