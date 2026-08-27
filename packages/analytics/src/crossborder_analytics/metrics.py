"""Versioned, deterministic advertising, profit, and inventory formulas."""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import Field, model_validator

from crossborder_domain.common import StrictDomainModel

RATIO_QUANTUM = Decimal("0.0001")
MONEY_QUANTUM = Decimal("0.01")
FORMULA_VERSION = "2026.08.1"


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return (numerator / denominator).quantize(RATIO_QUANTUM, rounding=ROUND_HALF_UP)


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class AdMetricInput(StrictDomainModel):
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    spend: Decimal = Field(ge=0)
    orders: int = Field(ge=0)
    revenue: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_funnel(self) -> "AdMetricInput":
        if self.clicks > self.impressions:
            raise ValueError("clicks 不能大于 impressions")
        return self


class AdMetricResult(StrictDomainModel):
    formula_version: str = FORMULA_VERSION
    impressions: int
    clicks: int
    spend: Decimal
    orders: int
    revenue: Decimal
    ctr: Decimal | None
    cpc: Decimal | None
    cpm: Decimal | None
    cvr: Decimal | None
    cpa: Decimal | None
    roas: Decimal | None


def calculate_ad_metrics(metric: AdMetricInput) -> AdMetricResult:
    impressions = Decimal(metric.impressions)
    clicks = Decimal(metric.clicks)
    orders = Decimal(metric.orders)
    return AdMetricResult(
        impressions=metric.impressions,
        clicks=metric.clicks,
        spend=_money(metric.spend),
        orders=metric.orders,
        revenue=_money(metric.revenue),
        ctr=_ratio(clicks, impressions),
        cpc=_ratio(metric.spend, clicks),
        cpm=_ratio(metric.spend * 1000, impressions),
        cvr=_ratio(orders, clicks),
        cpa=_ratio(metric.spend, orders),
        roas=_ratio(metric.revenue, metric.spend),
    )


class ContributionProfitInput(StrictDomainModel):
    gross_revenue: Decimal = Field(ge=0)
    discounts: Decimal = Field(default=Decimal(0), ge=0)
    product_cost: Decimal = Field(default=Decimal(0), ge=0)
    platform_fee: Decimal = Field(default=Decimal(0), ge=0)
    payment_fee: Decimal = Field(default=Decimal(0), ge=0)
    logistics_cost: Decimal = Field(default=Decimal(0), ge=0)
    tax: Decimal = Field(default=Decimal(0), ge=0)
    refund_loss: Decimal = Field(default=Decimal(0), ge=0)
    ad_spend: Decimal = Field(default=Decimal(0), ge=0)

    @model_validator(mode="after")
    def validate_discounts(self) -> "ContributionProfitInput":
        if self.discounts > self.gross_revenue:
            raise ValueError("discounts 不能大于 gross_revenue")
        return self


class ContributionProfitResult(StrictDomainModel):
    formula_version: str = FORMULA_VERSION
    net_revenue: Decimal
    pre_ad_contribution: Decimal
    contribution_profit: Decimal
    contribution_margin_rate: Decimal | None
    break_even_roas: Decimal | None


def calculate_contribution_profit(value: ContributionProfitInput) -> ContributionProfitResult:
    net_revenue = value.gross_revenue - value.discounts
    non_ad_costs = (
        value.product_cost
        + value.platform_fee
        + value.payment_fee
        + value.logistics_cost
        + value.tax
        + value.refund_loss
    )
    pre_ad_contribution = net_revenue - non_ad_costs
    contribution_profit = pre_ad_contribution - value.ad_spend
    contribution_margin_rate = _ratio(contribution_profit, net_revenue)
    pre_ad_margin_rate = _ratio(pre_ad_contribution, net_revenue)
    break_even_roas = (
        _ratio(Decimal(1), pre_ad_margin_rate)
        if pre_ad_margin_rate is not None and pre_ad_margin_rate > 0
        else None
    )
    return ContributionProfitResult(
        net_revenue=_money(net_revenue),
        pre_ad_contribution=_money(pre_ad_contribution),
        contribution_profit=_money(contribution_profit),
        contribution_margin_rate=contribution_margin_rate,
        break_even_roas=break_even_roas,
    )


class InventoryInput(StrictDomainModel):
    sellable_inventory: int = Field(ge=0)
    inbound_inventory: int = Field(default=0, ge=0)
    trailing_units_sold: int = Field(ge=0)
    trailing_window_days: int = Field(gt=0)
    lead_time_days: int = Field(ge=0)


class InventoryResult(StrictDomainModel):
    formula_version: str = FORMULA_VERSION
    daily_sales_velocity: Decimal
    inventory_cover_days: Decimal | None
    projected_inventory_before_arrival: Decimal
    projected_inventory_at_arrival: Decimal
    stockout_before_arrival: bool


def calculate_inventory_health(value: InventoryInput) -> InventoryResult:
    velocity = _ratio(Decimal(value.trailing_units_sold), Decimal(value.trailing_window_days))
    daily_velocity = velocity or Decimal(0)
    cover_days = (
        _ratio(Decimal(value.sellable_inventory), daily_velocity) if daily_velocity > 0 else None
    )
    projected_before_arrival = (
        Decimal(value.sellable_inventory) - daily_velocity * value.lead_time_days
    )
    projected_at_arrival = projected_before_arrival + value.inbound_inventory
    return InventoryResult(
        daily_sales_velocity=daily_velocity,
        inventory_cover_days=cover_days,
        projected_inventory_before_arrival=projected_before_arrival.quantize(
            RATIO_QUANTUM, rounding=ROUND_HALF_UP
        ),
        projected_inventory_at_arrival=projected_at_arrival.quantize(
            RATIO_QUANTUM, rounding=ROUND_HALF_UP
        ),
        stockout_before_arrival=projected_before_arrival <= 0 and daily_velocity > 0,
    )
