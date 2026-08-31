"""Canonical field aliases and deterministic mapping confirmation."""

import hashlib
import json
import re
import unicodedata
from collections import Counter

from crossborder_domain import ColumnMapping, DataDomain, MappingStatus

ADVERTISING_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "report_date": ("日期", "报告日期", "统计日期", "date", "day", "report date", "stat_time_day"),
    "campaign_id": (
        "广告系列id",
        "广告计划id",
        "推广系列id",
        "campaign id",
        "campaign_id",
    ),
    "campaign_name": (
        "广告系列名称",
        "广告计划名称",
        "campaign name",
        "campaign_name",
    ),
    "ad_group_id": ("广告组id", "ad group id", "adgroup id", "adgroup_id", "ad_group_id"),
    "ad_id": ("广告id", "创意id", "ad id", "ad_id"),
    "currency": ("币种", "货币", "currency", "currency code"),
    "impressions": ("展示次数", "展现次数", "曝光量", "impressions", "impression"),
    "clicks": ("点击次数", "点击量", "clicks", "click"),
    "spend": ("消耗", "花费", "广告成本", "spend", "cost"),
    "orders": ("订单数", "购买数", "成交订单数", "orders", "conversions", "purchase"),
    "revenue": (
        "成交金额",
        "总收入",
        "广告成交额",
        "gmv",
        "revenue",
        "purchase value",
        "gross revenue",
    ),
}

REQUIRED_ADVERTISING_FIELDS = frozenset(
    {
        "report_date",
        "campaign_id",
        "currency",
        "impressions",
        "clicks",
        "spend",
        "orders",
        "revenue",
    }
)

DATASET_FIELD_ALIASES: dict[DataDomain, dict[str, tuple[str, ...]]] = {
    DataDomain.ORDERS: {
        "order_id": ("订单id", "订单编号", "order id", "order_id"),
        "order_item_id": ("订单明细id", "子订单id", "order item id", "order_item_id"),
        "product_id": ("商品id", "product id", "product_id"),
        "sku": ("商家sku", "seller sku", "sku"),
        "ordered_at": ("下单时间", "订单时间", "created time", "ordered_at"),
        "source_timezone": ("源时区", "时区", "timezone", "source_timezone"),
        "market": ("市场", "站点", "国家", "market", "country"),
        "currency": ("币种", "currency"),
        "quantity": ("数量", "商品数量", "quantity", "qty"),
        "unit_price": ("商品单价", "单价", "unit price", "unit_price"),
        "gross_revenue": ("订单金额", "商品金额", "gross revenue", "gross_revenue", "gmv"),
        "discount": ("折扣", "优惠金额", "discount"),
        "status": ("订单状态", "status"),
    },
    DataDomain.PRODUCTS: {
        "product_id": ("商品id", "product id", "product_id"),
        "sku": ("商家sku", "seller sku", "sku"),
        "title": ("商品标题", "商品名称", "title", "product name"),
        "category": ("类目", "商品类目", "category"),
        "market": ("市场", "站点", "market", "country"),
        "currency": ("币种", "currency"),
        "unit_price": ("售价", "商品单价", "unit price", "price"),
        "status": ("商品状态", "status"),
    },
    DataDomain.COSTS: {
        "sku": ("商家sku", "seller sku", "sku"),
        "effective_date": ("生效日期", "成本日期", "effective date", "effective_date"),
        "currency": ("币种", "currency"),
        "product_cost": ("商品成本", "采购成本", "product cost", "cogs"),
        "platform_fee_rate": ("平台费率", "platform fee rate", "platform_fee_rate"),
        "payment_fee_rate": ("支付费率", "payment fee rate", "payment_fee_rate"),
        "logistics_cost": ("物流成本", "运费", "logistics cost", "shipping cost"),
        "tax_rate": ("税率", "tax rate", "tax_rate"),
    },
    DataDomain.INVENTORY: {
        "sku": ("商家sku", "seller sku", "sku"),
        "snapshot_date": ("快照日期", "库存日期", "snapshot date", "snapshot_date"),
        "warehouse_code": ("仓库编码", "仓库", "warehouse code", "warehouse"),
        "sellable_inventory": ("可售库存", "可用库存", "sellable inventory", "available"),
        "inbound_inventory": ("在途库存", "入库中", "inbound inventory", "inbound"),
        "safety_stock": ("安全库存", "safety stock", "safety_stock"),
        "lead_time_days": ("交期天数", "采购交期", "lead time days", "lead_time_days"),
    },
    DataDomain.REFUNDS: {
        "refund_id": ("退款id", "退款编号", "refund id", "refund_id"),
        "order_id": ("订单id", "订单编号", "order id", "order_id"),
        "order_item_id": ("订单明细id", "子订单id", "order item id", "order_item_id"),
        "refunded_at": ("退款时间", "refunded at", "refund time"),
        "source_timezone": ("源时区", "时区", "timezone", "source_timezone"),
        "currency": ("币种", "currency"),
        "refund_amount": ("退款金额", "refund amount", "refund_amount"),
        "reason": ("退款原因", "原因", "refund reason", "reason"),
    },
    DataDomain.REVIEWS: {
        "review_id": ("评价id", "评论id", "review id", "review_id"),
        "product_id": ("商品id", "product id", "product_id"),
        "reviewed_at": ("评价时间", "评论时间", "reviewed at", "review time"),
        "source_timezone": ("源时区", "时区", "timezone", "source_timezone"),
        "rating": ("评分", "星级", "rating", "stars"),
        "content": ("评价内容", "评论内容", "review content", "content"),
        "market": ("市场", "站点", "market", "country"),
        "language": ("语言", "language", "lang"),
    },
    DataDomain.CURRENCY_RATES: {
        "rate_date": ("汇率日期", "日期", "rate date", "rate_date"),
        "base_currency": ("基准币种", "原币", "base currency", "base_currency"),
        "quote_currency": ("报价币种", "目标币种", "quote currency", "quote_currency"),
        "rate": ("汇率", "exchange rate", "rate"),
        "source": ("汇率来源", "来源", "source", "provider"),
    },
    DataDomain.CREATIVES: {
        "creative_id": ("素材id", "创意id", "creative id", "creative_id"),
        "name": ("素材名称", "创意名称", "name", "creative name"),
        "media_type": ("素材类型", "媒体类型", "media type", "media_type"),
        "product_id": ("商品id", "product id", "product_id"),
        "created_at": ("创建时间", "created at", "create time"),
        "source_timezone": ("源时区", "时区", "timezone", "source_timezone"),
        "language": ("语言", "language", "lang"),
        "market": ("市场", "站点", "market", "country"),
        "storage_uri": ("素材地址", "存储地址", "storage uri", "url", "uri"),
    },
}

DATASET_REQUIRED_FIELDS: dict[DataDomain, frozenset[str]] = {
    DataDomain.ORDERS: frozenset(DATASET_FIELD_ALIASES[DataDomain.ORDERS]) - {"discount"},
    DataDomain.PRODUCTS: frozenset(DATASET_FIELD_ALIASES[DataDomain.PRODUCTS]),
    DataDomain.COSTS: frozenset(DATASET_FIELD_ALIASES[DataDomain.COSTS]),
    DataDomain.INVENTORY: frozenset(DATASET_FIELD_ALIASES[DataDomain.INVENTORY]),
    DataDomain.REFUNDS: frozenset(DATASET_FIELD_ALIASES[DataDomain.REFUNDS]),
    DataDomain.REVIEWS: frozenset(DATASET_FIELD_ALIASES[DataDomain.REVIEWS]),
    DataDomain.CURRENCY_RATES: frozenset(DATASET_FIELD_ALIASES[DataDomain.CURRENCY_RATES]),
    DataDomain.CREATIVES: frozenset(DATASET_FIELD_ALIASES[DataDomain.CREATIVES]) - {"product_id"},
}

DATASET_SCHEMA_VERSION = "2026.08.1"


def normalize_header(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return re.sub(r"[\s_\-:\u2013\u2014/\\()\[\]]+", "", normalized)


def _alias_index() -> dict[str, str]:
    return {
        normalize_header(alias): canonical
        for canonical, aliases in ADVERTISING_FIELD_ALIASES.items()
        for alias in (canonical, *aliases)
    }


ALIAS_INDEX = _alias_index()
DATASET_ALIAS_INDEX = {
    domain: {
        normalize_header(alias): canonical
        for canonical, aliases in fields.items()
        for alias in (canonical, *aliases)
    }
    for domain, fields in DATASET_FIELD_ALIASES.items()
}


def recognized_field(header: object) -> str | None:
    return ALIAS_INDEX.get(normalize_header(header))


def map_advertising_headers(headers: list[str]) -> list[ColumnMapping]:
    return _map_headers(headers, ALIAS_INDEX)


def recognized_dataset_field(domain: DataDomain, header: object) -> str | None:
    if domain is DataDomain.ADVERTISING:
        return recognized_field(header)
    return DATASET_ALIAS_INDEX.get(domain, {}).get(normalize_header(header))


def map_dataset_headers(domain: DataDomain, headers: list[str]) -> list[ColumnMapping]:
    if domain is DataDomain.ADVERTISING:
        return map_advertising_headers(headers)
    return _map_headers(headers, DATASET_ALIAS_INDEX.get(domain, {}))


def mapping_is_usable(mapping: ColumnMapping) -> bool:
    return mapping.status in {MappingStatus.AUTOMATIC, MappingStatus.CONFIRMED}


def mapping_signature(mappings: list[ColumnMapping]) -> str:
    payload = [
        {
            "source_column": mapping.source_column,
            "canonical_field": mapping.canonical_field,
        }
        for mapping in mappings
    ]
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def apply_mapping_overrides(
    mappings: list[ColumnMapping],
    overrides: dict[str, str | None] | None,
    allowed_fields: set[str] | frozenset[str],
) -> list[ColumnMapping]:
    if not overrides:
        return mappings

    source_columns = {mapping.source_column for mapping in mappings}
    unknown_sources = sorted(set(overrides) - source_columns)
    if unknown_sources:
        raise ValueError(f"映射包含文件中不存在的源列：{', '.join(unknown_sources)}")
    invalid_targets = sorted(
        {
            target
            for target in overrides.values()
            if target is not None and target not in allowed_fields
        }
    )
    if invalid_targets:
        raise ValueError(f"映射包含不支持的标准字段：{', '.join(invalid_targets)}")

    result: list[ColumnMapping] = []
    for mapping in mappings:
        if mapping.source_column not in overrides:
            result.append(mapping)
            continue
        target = overrides[mapping.source_column]
        result.append(
            ColumnMapping(
                source_column=mapping.source_column,
                canonical_field=target,
                status=MappingStatus.CONFIRMED if target else MappingStatus.UNMAPPED,
                confidence=1 if target else 0,
            )
        )

    counts = Counter(
        mapping.canonical_field for mapping in result if mapping.canonical_field is not None
    )
    return [
        mapping.model_copy(update={"status": MappingStatus.NEEDS_REVIEW, "confidence": 0.5})
        if mapping.canonical_field and counts[mapping.canonical_field] > 1
        else mapping
        for mapping in result
    ]


def _map_headers(headers: list[str], alias_index: dict[str, str]) -> list[ColumnMapping]:
    candidates = [alias_index.get(normalize_header(header)) for header in headers]
    counts = Counter(field for field in candidates if field is not None)
    mappings: list[ColumnMapping] = []
    for source, canonical in zip(headers, candidates, strict=True):
        if canonical is None:
            mappings.append(
                ColumnMapping(
                    source_column=source,
                    canonical_field=None,
                    status=MappingStatus.UNMAPPED,
                    confidence=0,
                )
            )
        elif counts[canonical] > 1:
            mappings.append(
                ColumnMapping(
                    source_column=source,
                    canonical_field=canonical,
                    status=MappingStatus.NEEDS_REVIEW,
                    confidence=0.5,
                )
            )
        else:
            mappings.append(
                ColumnMapping(
                    source_column=source,
                    canonical_field=canonical,
                    status=MappingStatus.AUTOMATIC,
                    confidence=1,
                )
            )
    return mappings
