"""Versioned deterministic business metric endpoints."""

from fastapi import APIRouter

from crossborder_analytics import (
    AdMetricInput,
    AdMetricResult,
    ContributionProfitInput,
    ContributionProfitResult,
    InventoryInput,
    InventoryResult,
    calculate_ad_metrics,
    calculate_contribution_profit,
    calculate_inventory_health,
)
from crossborder_api.schemas import ApiResponse

router = APIRouter(prefix="/metrics", tags=["business-metrics"])


@router.post("/advertising", response_model=ApiResponse[AdMetricResult])
async def advertising_metrics(value: AdMetricInput) -> ApiResponse[AdMetricResult]:
    return ApiResponse(data=calculate_ad_metrics(value))


@router.post("/contribution-profit", response_model=ApiResponse[ContributionProfitResult])
async def contribution_profit(
    value: ContributionProfitInput,
) -> ApiResponse[ContributionProfitResult]:
    return ApiResponse(data=calculate_contribution_profit(value))


@router.post("/inventory-health", response_model=ApiResponse[InventoryResult])
async def inventory_health(value: InventoryInput) -> ApiResponse[InventoryResult]:
    return ApiResponse(data=calculate_inventory_health(value))
