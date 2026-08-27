"""Advertising report preview, normalization, and quality checks."""

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from crossborder_analytics import AdMetricInput, calculate_ad_metrics
from crossborder_connectors.mapping import (
    REQUIRED_ADVERTISING_FIELDS,
    map_advertising_headers,
    recognized_field,
)
from crossborder_connectors.tabular import read_tabular
from crossborder_domain import (
    AdvertisingIngestionPreview,
    AdvertisingRecord,
    ColumnMapping,
    DataQualityIssue,
    MappingStatus,
    QualitySeverity,
)

HEADER_SCAN_LIMIT = 20


def _non_empty(row: list[Any]) -> bool:
    return any(value is not None and str(value).strip() for value in row)


def _find_header(rows: list[list[Any]]) -> tuple[int, list[str]]:
    candidates: list[tuple[int, int, list[str]]] = []
    for index, row in enumerate(rows[:HEADER_SCAN_LIMIT]):
        headers = [str(value).strip() if value is not None else "" for value in row]
        score = sum(recognized_field(header) is not None for header in headers)
        candidates.append((score, index, headers))
    if not candidates:
        raise ValueError("报表没有可读取的数据")
    score, index, headers = max(candidates, key=lambda item: (item[0], -item[1]))
    if score < 3:
        raise ValueError("未识别到广告报表表头，至少需要匹配 3 个标准字段")
    return index, headers


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue
    raise ValueError("日期格式无法识别")


def _parse_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    raw = re.sub(r"[^0-9.\-]", "", str(value or "").strip())
    if not raw:
        raise ValueError("数值为空")
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("数值格式无法识别") from exc


def _parse_int(value: Any) -> int:
    parsed = _parse_decimal(value)
    if parsed != parsed.to_integral_value():
        raise ValueError("必须为整数")
    return int(parsed)


def _idempotency_key(values: dict[str, Any]) -> str:
    fields = (
        "report_date",
        "campaign_id",
        "ad_group_id",
        "ad_id",
        "currency",
        "impressions",
        "clicks",
        "spend",
        "orders",
        "revenue",
    )
    payload = "|".join(str(values.get(field, "")) for field in fields)
    return hashlib.sha256(payload.encode()).hexdigest()


def _row_values(row: list[Any], mappings: list[ColumnMapping]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for index, mapping in enumerate(mappings):
        if (
            mapping.canonical_field
            and mapping.status is MappingStatus.AUTOMATIC
            and mapping.canonical_field not in values
        ):
            values[mapping.canonical_field] = row[index] if index < len(row) else None
    return values


def _normalize_record(values: dict[str, Any], row_number: int) -> AdvertisingRecord:
    normalized: dict[str, Any] = {
        "report_date": _parse_date(values.get("report_date")),
        "campaign_id": str(values.get("campaign_id") or "").strip(),
        "campaign_name": str(values.get("campaign_name") or "").strip() or None,
        "ad_group_id": str(values.get("ad_group_id") or "").strip() or None,
        "ad_id": str(values.get("ad_id") or "").strip() or None,
        "currency": str(values.get("currency") or "").strip().upper(),
        "impressions": _parse_int(values.get("impressions")),
        "clicks": _parse_int(values.get("clicks")),
        "spend": _parse_decimal(values.get("spend")),
        "orders": _parse_int(values.get("orders")),
        "revenue": _parse_decimal(values.get("revenue")),
        "source_row_number": row_number,
    }
    normalized["idempotency_key"] = _idempotency_key(normalized)
    return AdvertisingRecord.model_validate(normalized)


def preview_advertising_file(content: bytes, filename: str) -> AdvertisingIngestionPreview:
    table = read_tabular(content, filename)
    header_index, headers = _find_header(table.rows)
    mappings = map_advertising_headers(headers)
    mapped_fields = {
        mapping.canonical_field for mapping in mappings if mapping.status is MappingStatus.AUTOMATIC
    }
    missing_fields = sorted(REQUIRED_ADVERTISING_FIELDS - mapped_fields)
    issues = [
        DataQualityIssue(
            code="missing_required_field",
            severity=QualitySeverity.ERROR,
            message=f"缺少必填字段：{field}",
            column=field,
        )
        for field in missing_fields
    ]
    for mapping in mappings:
        if mapping.status is MappingStatus.NEEDS_REVIEW:
            issues.append(
                DataQualityIssue(
                    code="duplicate_mapping",
                    severity=QualitySeverity.ERROR,
                    message=f"多个源列映射到 {mapping.canonical_field}，需要人工确认",
                    column=mapping.source_column,
                )
            )

    source_rows = [
        (index + 1, row)
        for index, row in enumerate(table.rows[header_index + 1 :], start=header_index + 1)
        if _non_empty(row)
    ]
    records: list[AdvertisingRecord] = []
    seen_keys: set[str] = set()
    if not missing_fields and not any(
        mapping.status is MappingStatus.NEEDS_REVIEW for mapping in mappings
    ):
        for row_number, row in source_rows:
            try:
                record = _normalize_record(_row_values(row, mappings), row_number)
                if record.idempotency_key in seen_keys:
                    issues.append(
                        DataQualityIssue(
                            code="duplicate_row",
                            severity=QualitySeverity.WARNING,
                            message="该行与文件中已接收的数据重复，已跳过",
                            row_number=row_number,
                        )
                    )
                    continue
                seen_keys.add(record.idempotency_key)
                records.append(record)
            except (ValueError, ValidationError) as exc:
                issues.append(
                    DataQualityIssue(
                        code="invalid_row",
                        severity=QualitySeverity.ERROR,
                        message=str(exc),
                        row_number=row_number,
                    )
                )

    aggregate = calculate_ad_metrics(
        AdMetricInput(
            impressions=sum(record.impressions for record in records),
            clicks=sum(record.clicks for record in records),
            spend=sum((record.spend for record in records), Decimal(0)),
            orders=sum(record.orders for record in records),
            revenue=sum((record.revenue for record in records), Decimal(0)),
        )
    ).model_dump()
    return AdvertisingIngestionPreview(
        filename=filename,
        header_row_number=header_index + 1,
        source_row_count=len(source_rows),
        accepted_row_count=len(records),
        rejected_row_count=len(source_rows) - len(records),
        mappings=mappings,
        unknown_columns=[
            mapping.source_column
            for mapping in mappings
            if mapping.status is MappingStatus.UNMAPPED and mapping.source_column
        ],
        issues=issues,
        records=records,
        aggregate_metrics=aggregate,
    )
