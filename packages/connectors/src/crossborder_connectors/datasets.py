"""Schema-driven preview for non-advertising business datasets."""

import hashlib
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from crossborder_connectors.mapping import (
    DATASET_REQUIRED_FIELDS,
    DATASET_SCHEMA_VERSION,
    map_dataset_headers,
    recognized_dataset_field,
)
from crossborder_connectors.tabular import read_tabular
from crossborder_connectors.values import (
    parse_date,
    parse_datetime,
    parse_decimal,
    parse_int,
    parse_rate,
    stable_record_key,
    text_value,
)
from crossborder_domain import (
    ColumnMapping,
    CostRecord,
    CreativeRecord,
    CurrencyRateRecord,
    DataDomain,
    DataQualityIssue,
    DatasetIngestionPreview,
    InventoryRecord,
    MappingStatus,
    OrderRecord,
    ProductRecord,
    QualitySeverity,
    RefundRecord,
    ReviewRecord,
    StandardRecord,
)

HEADER_SCAN_LIMIT = 20


def _find_header(domain: DataDomain, rows: list[list[Any]]) -> tuple[int, list[str]]:
    candidates: list[tuple[int, int, list[str]]] = []
    for index, row in enumerate(rows[:HEADER_SCAN_LIMIT]):
        headers = [str(value).strip() if value is not None else "" for value in row]
        score = sum(recognized_dataset_field(domain, header) is not None for header in headers)
        candidates.append((score, index, headers))
    if not candidates:
        raise ValueError("报表没有可读取的数据")
    score, index, headers = max(candidates, key=lambda item: (item[0], -item[1]))
    if score < 3:
        raise ValueError(f"未识别到 {domain.value} 报表表头，至少需要匹配 3 个标准字段")
    return index, headers


def _non_empty(row: list[Any]) -> bool:
    return any(value is not None and str(value).strip() for value in row)


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


def _with_lineage(values: dict[str, Any], row_number: int) -> dict[str, Any]:
    normalized = {**values, "source_row_number": row_number}
    normalized["idempotency_key"] = stable_record_key(values)
    return normalized


def _normalize_order(values: dict[str, Any], row_number: int) -> OrderRecord:
    timezone_name = text_value(values.get("source_timezone"))
    normalized = {
        "order_id": text_value(values.get("order_id")),
        "order_item_id": text_value(values.get("order_item_id")),
        "product_id": text_value(values.get("product_id")),
        "sku": text_value(values.get("sku")),
        "ordered_at": parse_datetime(values.get("ordered_at"), timezone_name),
        "source_timezone": timezone_name,
        "market": text_value(values.get("market")).upper(),
        "currency": text_value(values.get("currency")).upper(),
        "quantity": parse_int(values.get("quantity")),
        "unit_price": parse_decimal(values.get("unit_price")),
        "gross_revenue": parse_decimal(values.get("gross_revenue")),
        "discount": parse_decimal(values.get("discount", 0)),
        "status": text_value(values.get("status")).lower(),
    }
    return OrderRecord.model_validate(_with_lineage(normalized, row_number))


def _normalize_product(values: dict[str, Any], row_number: int) -> ProductRecord:
    normalized = {
        "product_id": text_value(values.get("product_id")),
        "sku": text_value(values.get("sku")),
        "title": text_value(values.get("title")),
        "category": text_value(values.get("category")),
        "market": text_value(values.get("market")).upper(),
        "currency": text_value(values.get("currency")).upper(),
        "unit_price": parse_decimal(values.get("unit_price")),
        "status": text_value(values.get("status")).lower(),
    }
    return ProductRecord.model_validate(_with_lineage(normalized, row_number))


def _normalize_cost(values: dict[str, Any], row_number: int) -> CostRecord:
    normalized = {
        "sku": text_value(values.get("sku")),
        "effective_date": parse_date(values.get("effective_date")),
        "currency": text_value(values.get("currency")).upper(),
        "product_cost": parse_decimal(values.get("product_cost")),
        "platform_fee_rate": parse_rate(values.get("platform_fee_rate")),
        "payment_fee_rate": parse_rate(values.get("payment_fee_rate")),
        "logistics_cost": parse_decimal(values.get("logistics_cost")),
        "tax_rate": parse_rate(values.get("tax_rate")),
    }
    return CostRecord.model_validate(_with_lineage(normalized, row_number))


def _normalize_inventory(values: dict[str, Any], row_number: int) -> InventoryRecord:
    normalized = {
        "sku": text_value(values.get("sku")),
        "snapshot_date": parse_date(values.get("snapshot_date")),
        "warehouse_code": text_value(values.get("warehouse_code")),
        "sellable_inventory": parse_int(values.get("sellable_inventory")),
        "inbound_inventory": parse_int(values.get("inbound_inventory")),
        "safety_stock": parse_int(values.get("safety_stock")),
        "lead_time_days": parse_int(values.get("lead_time_days")),
    }
    return InventoryRecord.model_validate(_with_lineage(normalized, row_number))


def _normalize_refund(values: dict[str, Any], row_number: int) -> RefundRecord:
    timezone_name = text_value(values.get("source_timezone"))
    normalized = {
        "refund_id": text_value(values.get("refund_id")),
        "order_id": text_value(values.get("order_id")),
        "order_item_id": text_value(values.get("order_item_id")),
        "refunded_at": parse_datetime(values.get("refunded_at"), timezone_name),
        "source_timezone": timezone_name,
        "currency": text_value(values.get("currency")).upper(),
        "refund_amount": parse_decimal(values.get("refund_amount")),
        "reason": text_value(values.get("reason")),
    }
    return RefundRecord.model_validate(_with_lineage(normalized, row_number))


def _normalize_review(values: dict[str, Any], row_number: int) -> ReviewRecord:
    timezone_name = text_value(values.get("source_timezone"))
    normalized = {
        "review_id": text_value(values.get("review_id")),
        "product_id": text_value(values.get("product_id")),
        "reviewed_at": parse_datetime(values.get("reviewed_at"), timezone_name),
        "source_timezone": timezone_name,
        "rating": parse_int(values.get("rating")),
        "content": text_value(values.get("content")),
        "market": text_value(values.get("market")).upper(),
        "language": text_value(values.get("language")).lower(),
    }
    return ReviewRecord.model_validate(_with_lineage(normalized, row_number))


def _normalize_currency_rate(values: dict[str, Any], row_number: int) -> CurrencyRateRecord:
    normalized = {
        "rate_date": parse_date(values.get("rate_date")),
        "base_currency": text_value(values.get("base_currency")).upper(),
        "quote_currency": text_value(values.get("quote_currency")).upper(),
        "rate": parse_decimal(values.get("rate")),
        "source": text_value(values.get("source")),
    }
    return CurrencyRateRecord.model_validate(_with_lineage(normalized, row_number))


def _normalize_creative(values: dict[str, Any], row_number: int) -> CreativeRecord:
    timezone_name = text_value(values.get("source_timezone"))
    media_type = text_value(values.get("media_type")).lower()
    media_type = {"视频": "video", "图片": "image", "文本": "text"}.get(media_type, media_type)
    normalized = {
        "creative_id": text_value(values.get("creative_id")),
        "name": text_value(values.get("name")),
        "media_type": media_type,
        "product_id": text_value(values.get("product_id")) or None,
        "created_at": parse_datetime(values.get("created_at"), timezone_name),
        "source_timezone": timezone_name,
        "language": text_value(values.get("language")).lower(),
        "market": text_value(values.get("market")).upper(),
        "storage_uri": text_value(values.get("storage_uri")),
    }
    return CreativeRecord.model_validate(_with_lineage(normalized, row_number))


NORMALIZERS: dict[DataDomain, Callable[[dict[str, Any], int], StandardRecord]] = {
    DataDomain.ORDERS: _normalize_order,
    DataDomain.PRODUCTS: _normalize_product,
    DataDomain.COSTS: _normalize_cost,
    DataDomain.INVENTORY: _normalize_inventory,
    DataDomain.REFUNDS: _normalize_refund,
    DataDomain.REVIEWS: _normalize_review,
    DataDomain.CURRENCY_RATES: _normalize_currency_rate,
    DataDomain.CREATIVES: _normalize_creative,
}

BUSINESS_KEY_FIELDS: dict[DataDomain, tuple[str, ...]] = {
    DataDomain.ORDERS: ("order_item_id",),
    DataDomain.PRODUCTS: ("market", "product_id"),
    DataDomain.COSTS: ("sku", "effective_date"),
    DataDomain.INVENTORY: ("sku", "warehouse_code", "snapshot_date"),
    DataDomain.REFUNDS: ("refund_id",),
    DataDomain.REVIEWS: ("review_id",),
    DataDomain.CURRENCY_RATES: (
        "rate_date",
        "base_currency",
        "quote_currency",
        "source",
    ),
    DataDomain.CREATIVES: ("creative_id",),
}


def _business_key(record: StandardRecord, domain: DataDomain) -> tuple[str, ...]:
    values = record.model_dump()
    return tuple(str(values[field]) for field in BUSINESS_KEY_FIELDS[domain])


def preview_dataset_file(
    content: bytes, filename: str, domain: DataDomain
) -> DatasetIngestionPreview:
    if domain not in NORMALIZERS:
        raise ValueError(f"{domain.value} 请使用专用预检接口")
    table = read_tabular(content, filename)
    header_index, headers = _find_header(domain, table.rows)
    mappings = map_dataset_headers(domain, headers)
    mapped_fields = {
        mapping.canonical_field for mapping in mappings if mapping.status is MappingStatus.AUTOMATIC
    }
    missing_fields = sorted(DATASET_REQUIRED_FIELDS[domain] - mapped_fields)
    issues = [
        DataQualityIssue(
            code="missing_required_field",
            severity=QualitySeverity.ERROR,
            message=f"缺少必填字段：{field}",
            column=field,
        )
        for field in missing_fields
    ]
    duplicate_mappings = [
        mapping for mapping in mappings if mapping.status is MappingStatus.NEEDS_REVIEW
    ]
    issues.extend(
        DataQualityIssue(
            code="duplicate_mapping",
            severity=QualitySeverity.ERROR,
            message=f"多个源列映射到 {mapping.canonical_field}，需要人工确认",
            column=mapping.source_column,
        )
        for mapping in duplicate_mappings
    )
    source_rows = [
        (index + 1, row)
        for index, row in enumerate(table.rows[header_index + 1 :], start=header_index + 1)
        if _non_empty(row)
    ]
    records: list[StandardRecord] = []
    seen_keys: set[str] = set()
    seen_business_keys: set[tuple[str, ...]] = set()
    if not missing_fields and not duplicate_mappings:
        normalizer = NORMALIZERS[domain]
        for row_number, row in source_rows:
            try:
                record = normalizer(_row_values(row, mappings), row_number)
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
                business_key = _business_key(record, domain)
                if business_key in seen_business_keys:
                    issues.append(
                        DataQualityIssue(
                            code="duplicate_business_key",
                            severity=QualitySeverity.ERROR,
                            message="该行与文件中已有记录的业务主键相同，已跳过",
                            row_number=row_number,
                            value=list(business_key),
                        )
                    )
                    continue
                seen_keys.add(record.idempotency_key)
                seen_business_keys.add(business_key)
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
    return DatasetIngestionPreview(
        domain=domain,
        schema_version=DATASET_SCHEMA_VERSION,
        filename=filename,
        file_checksum_sha256=hashlib.sha256(content).hexdigest(),
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
    )
