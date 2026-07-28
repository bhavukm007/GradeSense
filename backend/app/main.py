from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.database.session import SessionFactory, dispose_engine
from app.middleware import ProductionMiddleware
from app.services.intelligence import IntelligenceService
from app.services.operations import AuditService
from app.services.registry import ModelRegistryService
from app.services.streaming import get_streaming_service

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def _record_lifecycle_audit(action: str) -> None:
    try:
        with SessionFactory() as session:
            AuditService().record(session, action, "application")
    except Exception:
        logger.exception("lifecycle_audit_failed", extra={"action": action})


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with SessionFactory() as session:
        IntelligenceService(settings, session).ensure_ready()
        ModelRegistryService().bootstrap_existing(session, settings)
    _record_lifecycle_audit("application_startup")
    stream = get_streaming_service(settings)
    await stream.start()
    logger.info("application_started", extra={"environment": settings.environment})
    yield
    await stream.stop()
    _record_lifecycle_audit("application_shutdown")
    dispose_engine()
    logger.info("application_stopped")


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI decision-support API for industrial paper grade transitions.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(ProductionMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_application()
