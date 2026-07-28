from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.schemas.system import RootResponse, VersionResponse
from app.services.system import SystemService, get_system_service

router = APIRouter(tags=["system"])
SystemServiceDependency = Depends(get_system_service)
_settings = get_settings()
HEALTH_PAYLOAD = {
    "status": "healthy",
    "service": _settings.app_name,
    "version": _settings.app_version,
    "environment": _settings.environment,
}


@router.get("/", response_model=RootResponse, summary="API root")
def root(service: SystemService = SystemServiceDependency) -> RootResponse:
    return service.root()


@router.get("/health", summary="Service health")
def health() -> JSONResponse:
    """Static liveness response: no database, models, filesystem, or settings access."""
    return JSONResponse(HEALTH_PAYLOAD)


@router.get("/version", response_model=VersionResponse, summary="Application version")
def version(service: SystemService = SystemServiceDependency) -> VersionResponse:
    return service.version()
