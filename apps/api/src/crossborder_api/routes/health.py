"""Liveness and readiness endpoints."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from crossborder_api.schemas import ApiResponse

router = APIRouter(prefix="/health", tags=["health"])


class HealthData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    version: str
    environment: str
    status: Literal["ok"]
    timestamp: datetime


def _health_data(request: Request) -> HealthData:
    settings = request.app.state.settings
    return HealthData(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        status="ok",
        timestamp=datetime.now(UTC),
    )


@router.get("/live", response_model=ApiResponse[HealthData])
async def liveness(request: Request) -> ApiResponse[HealthData]:
    return ApiResponse(data=_health_data(request))


@router.get("/ready", response_model=ApiResponse[HealthData])
async def readiness(request: Request) -> ApiResponse[HealthData]:
    # External dependency probes are added when database and Redis lifecycles
    # are wired. Until then this endpoint only confirms application readiness.
    return ApiResponse(data=_health_data(request))
