from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from tests.sample_factories import dataset_csv

from crossborder_connectors import preview_dataset_file
from crossborder_domain import DataDomain
from crossborder_persistence import Base
from crossborder_persistence.ingestion import IngestionConflictError, import_preview


def test_business_fact_metadata_contains_all_final_data_domains() -> None:
    expected_tables = {
        "ad_metrics_daily",
        "cost_profiles",
        "creatives",
        "currency_rates",
        "inventory_snapshots",
        "order_items",
        "orders",
        "products",
        "refunds",
        "reviews",
    }

    assert expected_tables <= set(Base.metadata.tables)
    assert "mapping_templates" in Base.metadata.tables
    mapping_constraints = {
        constraint.name
        for constraint in Base.metadata.tables["schema_mappings"].constraints
        if constraint.name
    }
    assert "uq_mapping_source_version_column" in mapping_constraints
    template_constraints = {
        constraint.name
        for constraint in Base.metadata.tables["mapping_templates"].constraints
        if constraint.name
    }
    assert "uq_mapping_template_source_name_version" in template_constraints


async def test_import_rejects_data_source_outside_organization_scope() -> None:
    content = dataset_csv(DataDomain.PRODUCTS)
    preview = preview_dataset_file(content, "products.csv", DataDomain.PRODUCTS)
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None

    with pytest.raises(IngestionConflictError, match="不属于当前组织"):
        await import_preview(
            cast(AsyncSession, session),
            organization_id=uuid4(),
            data_source_id=uuid4(),
            preview=preview,
        )

    session.add.assert_not_called()
