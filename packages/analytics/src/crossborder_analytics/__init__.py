"""Deterministic analytics used by tools and agents."""

from crossborder_analytics.metrics import (
    FORMULA_VERSION,
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

__all__ = [
    "FORMULA_VERSION",
    "AdMetricInput",
    "AdMetricResult",
    "ContributionProfitInput",
    "ContributionProfitResult",
    "InventoryInput",
    "InventoryResult",
    "calculate_ad_metrics",
    "calculate_contribution_profit",
    "calculate_inventory_health",
]
