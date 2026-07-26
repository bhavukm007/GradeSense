from fastapi import APIRouter

from app.api.routes.administration import router as administration_router
from app.api.routes.forecasting import router as forecasting_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.intervention import router as intervention_router
from app.api.routes.realtime import router as realtime_router
from app.api.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(intelligence_router)
api_router.include_router(realtime_router)
api_router.include_router(forecasting_router)
api_router.include_router(intervention_router)
api_router.include_router(administration_router)
