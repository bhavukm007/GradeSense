from typing import Literal

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class RootResponse(APIModel):
    name: str
    message: str
    documentation_url: str


class HealthResponse(APIModel):
    status: Literal["healthy"]
    service: str
    version: str
    environment: str


class VersionResponse(APIModel):
    name: str
    version: str
