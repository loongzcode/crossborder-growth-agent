from decimal import Decimal

from crossborder_analytics import (
    AdMetricInput,
    ContributionProfitInput,
    InventoryInput,
    calculate_ad_metrics,
    calculate_contribution_profit,
    calculate_inventory_health,
)


def test_ad_metrics_use_versioned_deterministic_formulas() -> None:
    result = calculate_ad_metrics(
        AdMetricInput(
            impressions=10_000,
            clicks=500,
            spend=Decimal("250"),
            orders=25,
            revenue=Decimal("1000"),
        )
    )

    assert result.ctr == Decimal("0.0500")
    assert result.cpc == Decimal("0.5000")
    assert result.cpm == Decimal("25.0000")
    assert result.cvr == Decimal("0.0500")
    assert result.cpa == Decimal("10.0000")
    assert result.roas == Decimal("4.0000")
    assert result.formula_version == "2026.08.1"


def test_zero_denominators_are_unknown_instead_of_fake_zero() -> None:
    result = calculate_ad_metrics(
        AdMetricInput(impressions=0, clicks=0, spend=0, orders=0, revenue=0)
    )

    assert result.ctr is None
    assert result.cpc is None
    assert result.cpa is None
    assert result.roas is None


def test_contribution_profit_exposes_break_even_roas() -> None:
    result = calculate_contribution_profit(
        ContributionProfitInput(
            gross_revenue=Decimal("1000"),
            product_cost=Decimal("300"),
            platform_fee=Decimal("100"),
            logistics_cost=Decimal("100"),
            ad_spend=Decimal("200"),
        )
    )

    assert result.pre_ad_contribution == Decimal("500.00")
    assert result.contribution_profit == Decimal("300.00")
    assert result.contribution_margin_rate == Decimal("0.3000")
    assert result.break_even_roas == Decimal("2.0000")


def test_inventory_health_flags_stockout_before_replenishment() -> None:
    result = calculate_inventory_health(
        InventoryInput(
            sellable_inventory=100,
            inbound_inventory=200,
            trailing_units_sold=140,
            trailing_window_days=14,
            lead_time_days=12,
        )
    )

    assert result.daily_sales_velocity == Decimal("10.0000")
    assert result.inventory_cover_days == Decimal("10.0000")
    assert result.projected_inventory_before_arrival == Decimal("-20.0000")
    assert result.projected_inventory_at_arrival == Decimal("180.0000")
    assert result.stockout_before_arrival is True
