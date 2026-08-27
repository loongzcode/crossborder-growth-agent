"""Canonical field aliases for advertising reports."""

import re
import unicodedata
from collections import Counter

from crossborder_domain import ColumnMapping, MappingStatus

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


def recognized_field(header: object) -> str | None:
    return ALIAS_INDEX.get(normalize_header(header))


def map_advertising_headers(headers: list[str]) -> list[ColumnMapping]:
    candidates = [recognized_field(header) for header in headers]
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
