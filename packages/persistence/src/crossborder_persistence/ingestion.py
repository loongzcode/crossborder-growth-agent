"""Transactional, organization-scoped ingestion and lineage queries."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from crossborder_analytics import FORMULA_VERSION
from crossborder_domain import (
    AdvertisingIngestionPreview,
    AdvertisingRecord,
    ColumnMapping,
    CostRecord,
    CreativeRecord,
    CurrencyRateRecord,
    DataDomain,
    DataQualityIssue,
    DatasetIngestionPreview,
    ImportStatus,
    IngestionImportResult,
    IngestionLineage,
    InventoryRecord,
    OrderRecord,
    ProductRecord,
    RefundRecord,
    ReviewRecord,
)
from crossborder_persistence.facts import (
    AdMetricDailyModel,
    CampaignModel,
    CostProfileModel,
    CreativeModel,
    CurrencyRateModel,
    DataQualityIssueModel,
    DataSourceModel,
    InventorySnapshotModel,
    OrderItemModel,
    OrderModel,
    ProductModel,
    RawBatchModel,
    RefundModel,
    ReviewModel,
    SchemaMappingModel,
    SyncJobModel,
)

Preview = AdvertisingIngestionPreview | DatasetIngestionPreview


class IngestionConflictError(ValueError):
    pass


class LineageNotFoundError(LookupError):
    pass


async def get_batch_lineage(
    session: AsyncSession, *, organization_id: UUID, raw_batch_id: UUID
) -> IngestionLineage:
    result = await session.execute(
        select(RawBatchModel, SyncJobModel, DataSourceModel)
        .join(SyncJobModel, SyncJobModel.id == RawBatchModel.sync_job_id)
        .join(DataSourceModel, DataSourceModel.id == RawBatchModel.data_source_id)
        .where(
            RawBatchModel.id == raw_batch_id,
            DataSourceModel.organization_id == organization_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise LineageNotFoundError("批次不存在或不属于当前组织")
    batch, job, source = row
    issue_rows = (
        await session.scalars(
            select(DataQualityIssueModel).where(DataQualityIssueModel.raw_batch_id == batch.id)
        )
    ).all()
    return IngestionLineage(
        organization_id=str(source.organization_id),
        data_source_id=str(source.id),
        data_source_name=source.name,
        provider=source.provider,
        domain=source.domain,
        sync_job_id=str(job.id),
        sync_status=job.status,
        raw_batch_id=str(batch.id),
        filename=batch.filename,
        file_checksum_sha256=batch.checksum_sha256,
        schema_version=batch.schema_version,
        header_row_number=batch.header_row_number,
        source_row_count=batch.row_count,
        accepted_row_count=job.accepted_rows,
        rejected_row_count=job.rejected_rows,
        created_at=batch.created_at,
        mappings=[ColumnMapping.model_validate(mapping) for mapping in batch.mapping_snapshot],
        issues=[
            DataQualityIssue(
                code=issue.code,
                severity=issue.severity,
                message=issue.message,
                row_number=issue.row_number,
                column=issue.column_name,
                value=issue.raw_value.get("value") if issue.raw_value else None,
            )
            for issue in issue_rows
        ],
    )


async def import_preview(
    session: AsyncSession,
    *,
    organization_id: UUID,
    data_source_id: UUID,
    preview: Preview,
) -> IngestionImportResult:
    source = await session.scalar(
        select(DataSourceModel).where(
            DataSourceModel.id == data_source_id,
            DataSourceModel.organization_id == organization_id,
        )
    )
    if source is None:
        raise IngestionConflictError("数据源不存在或不属于当前组织")
    if not source.enabled:
        raise IngestionConflictError("数据源已停用")
    if source.domain is not preview.domain:
        raise IngestionConflictError(
            f"数据源领域为 {source.domain.value}，不能导入 {preview.domain.value}"
        )
    if preview.rejected_row_count > 0:
        raise IngestionConflictError("预检仍有拒绝行，修复数据后才能确认导入")

    existing_batch = await session.scalar(
        select(RawBatchModel).where(
            RawBatchModel.data_source_id == data_source_id,
            RawBatchModel.checksum_sha256 == preview.file_checksum_sha256,
        )
    )
    if existing_batch is not None:
        return _import_result(
            ImportStatus.DUPLICATE,
            preview,
            existing_batch.sync_job_id,
            existing_batch.id,
            imported_rows=0,
        )

    now = datetime.now(UTC)
    sync_job = SyncJobModel(
        data_source_id=data_source_id,
        status="running",
        started_at=now,
        received_rows=preview.source_row_count,
        accepted_rows=preview.accepted_row_count,
        rejected_rows=preview.rejected_row_count,
    )
    session.add(sync_job)
    await session.flush()
    batch = RawBatchModel(
        data_source_id=data_source_id,
        sync_job_id=sync_job.id,
        filename=preview.filename,
        checksum_sha256=preview.file_checksum_sha256,
        storage_uri=None,
        schema_version=preview.schema_version,
        mapping_snapshot=[mapping.model_dump(mode="json") for mapping in preview.mappings],
        header_row_number=preview.header_row_number,
        row_count=preview.source_row_count,
    )
    session.add(batch)
    await session.flush()

    await _save_mappings(session, data_source_id, preview)
    session.add_all(
        DataQualityIssueModel(
            raw_batch_id=batch.id,
            code=issue.code,
            severity=issue.severity,
            message=issue.message,
            row_number=issue.row_number,
            column_name=issue.column,
            raw_value={"value": issue.value} if issue.value is not None else None,
        )
        for issue in preview.issues
    )
    await _persist_records(session, organization_id, batch.id, preview)
    sync_job.status = "completed"
    sync_job.finished_at = datetime.now(UTC)
    return _import_result(
        ImportStatus.IMPORTED,
        preview,
        sync_job.id,
        batch.id,
        imported_rows=preview.accepted_row_count,
    )


def _import_result(
    status: ImportStatus,
    preview: Preview,
    sync_job_id: UUID,
    raw_batch_id: UUID,
    *,
    imported_rows: int,
) -> IngestionImportResult:
    return IngestionImportResult(
        status=status,
        domain=preview.domain,
        sync_job_id=str(sync_job_id),
        raw_batch_id=str(raw_batch_id),
        source_row_count=preview.source_row_count,
        imported_row_count=imported_rows,
        rejected_row_count=preview.rejected_row_count,
        file_checksum_sha256=preview.file_checksum_sha256,
        lineage_path=f"/api/v1/ingestion/batches/{raw_batch_id}",
    )


async def _save_mappings(session: AsyncSession, data_source_id: UUID, preview: Preview) -> None:
    rows = [
        {
            "data_source_id": data_source_id,
            "source_column": mapping.source_column,
            "canonical_field": mapping.canonical_field,
            "status": mapping.status.value,
            "confidence": mapping.confidence,
            "mapping_version": preview.schema_version,
            "active": True,
        }
        for mapping in preview.mappings
    ]
    if not rows:
        return
    statement = pg_insert(SchemaMappingModel).values(rows)
    await session.execute(
        statement.on_conflict_do_update(
            constraint="uq_mapping_source_version_column",
            set_={
                "canonical_field": statement.excluded.canonical_field,
                "status": statement.excluded.status,
                "confidence": statement.excluded.confidence,
                "active": True,
            },
        )
    )


async def _persist_records(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, preview: Preview
) -> None:
    if preview.domain is DataDomain.ADVERTISING:
        advertising_records = [
            record for record in preview.records if isinstance(record, AdvertisingRecord)
        ]
        await _persist_advertising(session, organization_id, raw_batch_id, advertising_records)
        return
    records = preview.records
    if preview.domain is DataDomain.PRODUCTS:
        await _persist_products(session, organization_id, raw_batch_id, records)
    elif preview.domain is DataDomain.ORDERS:
        await _persist_orders(session, organization_id, raw_batch_id, records)
    elif preview.domain is DataDomain.COSTS:
        await _persist_costs(session, organization_id, raw_batch_id, records)
    elif preview.domain is DataDomain.INVENTORY:
        await _persist_inventory(session, organization_id, raw_batch_id, records)
    elif preview.domain is DataDomain.REFUNDS:
        await _persist_refunds(session, organization_id, raw_batch_id, records)
    elif preview.domain is DataDomain.REVIEWS:
        await _persist_reviews(session, organization_id, raw_batch_id, records)
    elif preview.domain is DataDomain.CURRENCY_RATES:
        await _persist_currency_rates(session, organization_id, raw_batch_id, records)
    elif preview.domain is DataDomain.CREATIVES:
        await _persist_creatives(session, organization_id, raw_batch_id, records)


async def _execute_upsert(
    session: AsyncSession,
    model: type[Any],
    rows: list[dict[str, Any]],
    *,
    constraint: str,
    update_fields: tuple[str, ...],
) -> None:
    if not rows:
        return
    statement = pg_insert(model).values(rows)
    await session.execute(
        statement.on_conflict_do_update(
            constraint=constraint,
            set_={field: getattr(statement.excluded, field) for field in update_fields},
        )
    )


async def _persist_advertising(
    session: AsyncSession,
    organization_id: UUID,
    raw_batch_id: UUID,
    records: list[AdvertisingRecord],
) -> None:
    campaigns = {
        record.campaign_id: {
            "organization_id": organization_id,
            "platform": "tiktok_ads",
            "external_id": record.campaign_id,
            "name": record.campaign_name,
        }
        for record in records
    }
    await _execute_upsert(
        session,
        CampaignModel,
        list(campaigns.values()),
        constraint="uq_campaign_external",
        update_fields=("name",),
    )
    rows = [
        {
            "organization_id": organization_id,
            "raw_batch_id": raw_batch_id,
            "report_date": record.report_date,
            "platform": "tiktok_ads",
            "campaign_external_id": record.campaign_id,
            "ad_group_external_id": record.ad_group_id or "",
            "ad_external_id": record.ad_id or "",
            "currency": record.currency,
            "impressions": record.impressions,
            "clicks": record.clicks,
            "spend": record.spend,
            "orders": record.orders,
            "revenue": record.revenue,
            "idempotency_key": record.idempotency_key,
            "formula_version": FORMULA_VERSION,
        }
        for record in records
    ]
    await _execute_upsert(
        session,
        AdMetricDailyModel,
        rows,
        constraint="uq_ad_metric_daily_grain",
        update_fields=(
            "raw_batch_id",
            "currency",
            "impressions",
            "clicks",
            "spend",
            "orders",
            "revenue",
            "idempotency_key",
            "formula_version",
        ),
    )


async def _persist_products(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    typed = [record for record in records if isinstance(record, ProductRecord)]
    rows = [
        {
            "organization_id": organization_id,
            "raw_batch_id": raw_batch_id,
            "external_id": record.product_id,
            "sku": record.sku,
            "title": record.title,
            "category": record.category,
            "market": record.market,
            "currency": record.currency,
            "unit_price": record.unit_price,
            "status": record.status,
            "source_row_number": record.source_row_number,
            "idempotency_key": record.idempotency_key,
        }
        for record in typed
    ]
    await _execute_upsert(
        session,
        ProductModel,
        rows,
        constraint="uq_product_external",
        update_fields=(
            "raw_batch_id",
            "sku",
            "title",
            "category",
            "currency",
            "unit_price",
            "status",
            "source_row_number",
            "idempotency_key",
        ),
    )


async def _persist_orders(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    typed = [record for record in records if isinstance(record, OrderRecord)]
    grouped: dict[str, OrderRecord] = {}
    for record in typed:
        grouped.setdefault(record.order_id, record)
    order_rows = [
        {
            "organization_id": organization_id,
            "raw_batch_id": raw_batch_id,
            "external_id": record.order_id,
            "ordered_at": record.ordered_at,
            "source_timezone": record.source_timezone,
            "market": record.market,
            "currency": record.currency,
            "status": record.status,
            "idempotency_key": record.idempotency_key,
        }
        for record in grouped.values()
    ]
    await _execute_upsert(
        session,
        OrderModel,
        order_rows,
        constraint="uq_order_external",
        update_fields=(
            "raw_batch_id",
            "ordered_at",
            "source_timezone",
            "market",
            "currency",
            "status",
            "idempotency_key",
        ),
    )
    order_result = await session.execute(
        select(OrderModel.external_id, OrderModel.id).where(
            OrderModel.organization_id == organization_id,
            OrderModel.external_id.in_(grouped),
        )
    )
    order_ids: dict[str, UUID] = {
        external_id: identifier for external_id, identifier in order_result.tuples()
    }
    product_result = await session.execute(
        select(ProductModel.external_id, ProductModel.market, ProductModel.id).where(
            ProductModel.organization_id == organization_id,
            ProductModel.external_id.in_({record.product_id for record in typed}),
        )
    )
    product_ids = {
        (external_id, market): identifier for external_id, market, identifier in product_result
    }
    item_rows = [
        {
            "organization_id": organization_id,
            "order_id": order_ids[record.order_id],
            "product_id": product_ids.get((record.product_id, record.market)),
            "raw_batch_id": raw_batch_id,
            "external_id": record.order_item_id,
            "product_external_id": record.product_id,
            "sku": record.sku,
            "quantity": record.quantity,
            "unit_price": record.unit_price,
            "gross_revenue": record.gross_revenue,
            "discount": record.discount,
            "source_row_number": record.source_row_number,
            "idempotency_key": record.idempotency_key,
        }
        for record in typed
    ]
    await _execute_upsert(
        session,
        OrderItemModel,
        item_rows,
        constraint="uq_order_item_external",
        update_fields=(
            "order_id",
            "product_id",
            "raw_batch_id",
            "product_external_id",
            "sku",
            "quantity",
            "unit_price",
            "gross_revenue",
            "discount",
            "source_row_number",
            "idempotency_key",
        ),
    )


async def _persist_costs(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    rows = [
        {
            "organization_id": organization_id,
            "raw_batch_id": raw_batch_id,
            **record.model_dump(exclude={"source_row_number", "idempotency_key"}),
            "source_row_number": record.source_row_number,
            "idempotency_key": record.idempotency_key,
        }
        for record in records
        if isinstance(record, CostRecord)
    ]
    await _execute_upsert(
        session,
        CostProfileModel,
        rows,
        constraint="uq_cost_profile_effective",
        update_fields=tuple(
            key for key in rows[0] if key not in {"organization_id", "sku", "effective_date"}
        )
        if rows
        else (),
    )


async def _persist_inventory(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    rows = [
        {"organization_id": organization_id, "raw_batch_id": raw_batch_id, **record.model_dump()}
        for record in records
        if isinstance(record, InventoryRecord)
    ]
    await _execute_upsert(
        session,
        InventorySnapshotModel,
        rows,
        constraint="uq_inventory_snapshot_grain",
        update_fields=tuple(
            key
            for key in rows[0]
            if key not in {"organization_id", "sku", "warehouse_code", "snapshot_date"}
        )
        if rows
        else (),
    )


async def _reference_maps(
    session: AsyncSession, organization_id: UUID
) -> tuple[dict[str, UUID], dict[str, UUID], dict[tuple[str, str], UUID]]:
    order_result = await session.execute(
        select(OrderModel.external_id, OrderModel.id).where(
            OrderModel.organization_id == organization_id
        )
    )
    orders: dict[str, UUID] = {
        external_id: identifier for external_id, identifier in order_result.tuples()
    }
    item_result = await session.execute(
        select(OrderItemModel.external_id, OrderItemModel.id).where(
            OrderItemModel.organization_id == organization_id
        )
    )
    items: dict[str, UUID] = {
        external_id: identifier for external_id, identifier in item_result.tuples()
    }
    products_result = await session.execute(
        select(ProductModel.external_id, ProductModel.market, ProductModel.id).where(
            ProductModel.organization_id == organization_id
        )
    )
    products = {
        (external_id, market): identifier for external_id, market, identifier in products_result
    }
    return orders, items, products


async def _persist_refunds(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    typed = [record for record in records if isinstance(record, RefundRecord)]
    order_ids, item_ids, _ = await _reference_maps(session, organization_id)
    rows = [
        {
            "organization_id": organization_id,
            "order_id": order_ids.get(record.order_id),
            "order_item_id": item_ids.get(record.order_item_id),
            "raw_batch_id": raw_batch_id,
            "external_id": record.refund_id,
            "order_external_id": record.order_id,
            "order_item_external_id": record.order_item_id,
            "refunded_at": record.refunded_at,
            "source_timezone": record.source_timezone,
            "currency": record.currency,
            "refund_amount": record.refund_amount,
            "reason": record.reason,
            "source_row_number": record.source_row_number,
            "idempotency_key": record.idempotency_key,
        }
        for record in typed
    ]
    await _execute_upsert(
        session,
        RefundModel,
        rows,
        constraint="uq_refund_external",
        update_fields=tuple(key for key in rows[0] if key not in {"organization_id", "external_id"})
        if rows
        else (),
    )


async def _persist_reviews(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    typed = [record for record in records if isinstance(record, ReviewRecord)]
    _, _, product_ids = await _reference_maps(session, organization_id)
    rows = [
        {
            "organization_id": organization_id,
            "product_id": product_ids.get((record.product_id, record.market)),
            "raw_batch_id": raw_batch_id,
            "external_id": record.review_id,
            "product_external_id": record.product_id,
            "reviewed_at": record.reviewed_at,
            "source_timezone": record.source_timezone,
            "rating": record.rating,
            "content": record.content,
            "market": record.market,
            "language": record.language,
            "source_row_number": record.source_row_number,
            "idempotency_key": record.idempotency_key,
        }
        for record in typed
    ]
    await _execute_upsert(
        session,
        ReviewModel,
        rows,
        constraint="uq_review_external",
        update_fields=tuple(key for key in rows[0] if key not in {"organization_id", "external_id"})
        if rows
        else (),
    )


async def _persist_currency_rates(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    rows = [
        {"organization_id": organization_id, "raw_batch_id": raw_batch_id, **record.model_dump()}
        for record in records
        if isinstance(record, CurrencyRateRecord)
    ]
    await _execute_upsert(
        session,
        CurrencyRateModel,
        rows,
        constraint="uq_currency_rate_grain",
        update_fields=("raw_batch_id", "rate", "source_row_number", "idempotency_key"),
    )


async def _persist_creatives(
    session: AsyncSession, organization_id: UUID, raw_batch_id: UUID, records: list[Any]
) -> None:
    typed = [record for record in records if isinstance(record, CreativeRecord)]
    _, _, product_ids = await _reference_maps(session, organization_id)
    rows = [
        {
            "organization_id": organization_id,
            "product_id": product_ids.get((record.product_id, record.market))
            if record.product_id
            else None,
            "raw_batch_id": raw_batch_id,
            "external_id": record.creative_id,
            "name": record.name,
            "media_type": record.media_type,
            "product_external_id": record.product_id,
            "source_created_at": record.created_at,
            "source_timezone": record.source_timezone,
            "language": record.language,
            "market": record.market,
            "storage_uri": record.storage_uri,
            "source_row_number": record.source_row_number,
            "idempotency_key": record.idempotency_key,
        }
        for record in typed
    ]
    await _execute_upsert(
        session,
        CreativeModel,
        rows,
        constraint="uq_creative_external",
        update_fields=tuple(key for key in rows[0] if key not in {"organization_id", "external_id"})
        if rows
        else (),
    )
