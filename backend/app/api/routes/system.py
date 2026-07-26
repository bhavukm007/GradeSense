from fastapi import APIRouter, Depends

from app.schemas.system import HealthResponse, RootResponse, VersionResponse
from app.services.system import SystemService, get_system_service

router = APIRouter(tags=["system"])
SystemServiceDependency = Depends(get_system_service)


@router.get("/", response_model=RootResponse, summary="API root")
def root(service: SystemService = SystemServiceDependency) -> RootResponse:
    return service.root()


@router.get("/health", response_model=HealthResponse, summary="Service health")
def health(service: SystemService = SystemServiceDependency) -> HealthResponse:
    return service.health()


@router.get("/version", response_model=VersionResponse, summary="Application version")
def version(service: SystemService = SystemServiceDependency) -> VersionResponse:
    return service.version()
