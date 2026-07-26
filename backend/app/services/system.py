from app.config.settings import Settings, get_settings
from app.schemas.system import HealthResponse, RootResponse, VersionResponse


class SystemService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def root(self) -> RootResponse:
        return RootResponse(
            name=self._settings.app_name,
            message="GradeSenseAI service is running.",
            documentation_url="/docs",
        )

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="healthy",
            service=self._settings.app_name,
            version=self._settings.app_version,
            environment=self._settings.environment,
        )

    def version(self) -> VersionResponse:
        return VersionResponse(name=self._settings.app_name, version=self._settings.app_version)


def get_system_service() -> SystemService:
    return SystemService(get_settings())
