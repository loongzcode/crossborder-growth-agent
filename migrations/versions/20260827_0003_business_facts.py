"""补齐跨境业务事实表与版本化字段映射。

Revision ID: 20260827_0003
Revises: 20260827_0002
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0003"
down_revision: str | None = "20260827_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def _lineage_columns() -> tuple[sa.Column[object], sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("raw_batch_id", sa.Uuid(), nullable=False),
    )


def upgrade() -> None:
    op.alter_column("raw_batches", "storage_uri", existing_type=sa.String(1024), nullable=True)
    op.add_column(
        "raw_batches",
        sa.Column(
            "schema_version",
            sa.String(length=32),
            server_default="2026.08.1",
            nullable=False,
        ),
    )
    op.alter_column("raw_batches", "schema_version", server_default=None)
    op.add_column(
        "raw_batches",
        sa.Column(
            "mapping_snapshot",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.alter_column("raw_batches", "mapping_snapshot", server_default=None)
    op.drop_constraint("uq_mapping_source_column", "schema_mappings", type_="unique")
    op.add_column(
        "schema_mappings",
        sa.Column(
            "mapping_version",
            sa.String(length=32),
            server_default="2026.08.1",
            nullable=False,
        ),
    )
    op.add_column(
        "schema_mappings",
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "schema_mappings", sa.Column("confirmed_by", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "schema_mappings",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_mapping_source_version_column",
        "schema_mappings",
        ["data_source_id", "mapping_version", "source_column"],
    )
    op.alter_column("schema_mappings", "mapping_version", server_default=None)
    op.alter_column("schema_mappings", "active", server_default=None)

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("category", sa.String(length=256), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "market", "external_id", name="uq_product_external"),
        sa.UniqueConstraint("organization_id", "market", "sku", name="uq_product_sku"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_product_idempotency"),
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"])
    op.create_index("ix_products_raw_batch_id", "products", ["raw_batch_id"])
    op.create_index("ix_products_sku", "products", ["sku"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("raw_batch_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_timezone", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "external_id", name="uq_order_external"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_order_idempotency"),
    )
    op.create_index("ix_orders_organization_id", "orders", ["organization_id"])
    op.create_index("ix_orders_raw_batch_id", "orders", ["raw_batch_id"])
    op.create_index("ix_orders_ordered_at", "orders", ["ordered_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("product_external_id", sa.String(length=128), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("gross_revenue", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("discount", sa.Numeric(precision=20, scale=4), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "external_id", name="uq_order_item_external"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_order_item_idempotency"),
    )
    for column in ("organization_id", "order_id", "product_id", "raw_batch_id", "sku"):
        op.create_index(f"ix_order_items_{column}", "order_items", [column])

    op.create_table(
        "cost_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("product_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("platform_fee_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("payment_fee_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("logistics_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "sku", "effective_date", name="uq_cost_profile_effective"
        ),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_cost_profile_idempotency"
        ),
    )
    for column in ("organization_id", "raw_batch_id", "sku", "effective_date"):
        op.create_index(f"ix_cost_profiles_{column}", "cost_profiles", [column])

    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("warehouse_code", sa.String(length=128), nullable=False),
        sa.Column("sellable_inventory", sa.BigInteger(), nullable=False),
        sa.Column("inbound_inventory", sa.BigInteger(), nullable=False),
        sa.Column("safety_stock", sa.BigInteger(), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "sku",
            "warehouse_code",
            "snapshot_date",
            name="uq_inventory_snapshot_grain",
        ),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_inventory_idempotency"),
    )
    for column in ("organization_id", "raw_batch_id", "sku", "snapshot_date"):
        op.create_index(f"ix_inventory_snapshots_{column}", "inventory_snapshots", [column])

    op.create_table(
        "refunds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("order_item_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("order_external_id", sa.String(length=128), nullable=False),
        sa.Column("order_item_external_id", sa.String(length=128), nullable=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_timezone", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("refund_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "external_id", name="uq_refund_external"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_refund_idempotency"),
    )
    for column in ("organization_id", "raw_batch_id", "order_external_id"):
        op.create_index(f"ix_refunds_{column}", "refunds", [column])

    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("product_external_id", sa.String(length=128), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_timezone", sa.String(length=64), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "external_id", name="uq_review_external"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_review_idempotency"),
    )
    for column in ("organization_id", "raw_batch_id", "product_external_id"):
        op.create_index(f"ix_reviews_{column}", "reviews", [column])

    op.create_table(
        "currency_rates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "rate_date",
            "base_currency",
            "quote_currency",
            "source",
            name="uq_currency_rate_grain",
        ),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_currency_rate_idempotency"
        ),
    )
    for column in ("organization_id", "raw_batch_id", "rate_date"):
        op.create_index(f"ix_currency_rates_{column}", "currency_rates", [column])

    op.create_table(
        "creatives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("product_external_id", sa.String(length=128), nullable=True),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_timezone", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        *_lineage_columns(),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["raw_batch_id"], ["raw_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "external_id", name="uq_creative_external"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_creative_idempotency"),
    )
    for column in ("organization_id", "raw_batch_id"):
        op.create_index(f"ix_creatives_{column}", "creatives", [column])


def downgrade() -> None:
    for table, indexes in (
        ("creatives", ("organization_id", "raw_batch_id")),
        ("currency_rates", ("organization_id", "raw_batch_id", "rate_date")),
        ("reviews", ("organization_id", "raw_batch_id", "product_external_id")),
        ("refunds", ("organization_id", "raw_batch_id", "order_external_id")),
        (
            "inventory_snapshots",
            ("organization_id", "raw_batch_id", "sku", "snapshot_date"),
        ),
        ("cost_profiles", ("organization_id", "raw_batch_id", "sku", "effective_date")),
        ("order_items", ("organization_id", "order_id", "product_id", "raw_batch_id", "sku")),
    ):
        for column in indexes:
            op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.drop_table(table)
    op.drop_index("ix_orders_ordered_at", table_name="orders")
    op.drop_index("ix_orders_raw_batch_id", table_name="orders")
    op.drop_index("ix_orders_organization_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_raw_batch_id", table_name="products")
    op.drop_index("ix_products_organization_id", table_name="products")
    op.drop_table("products")

    op.drop_constraint("uq_mapping_source_version_column", "schema_mappings", type_="unique")
    op.drop_column("schema_mappings", "confirmed_at")
    op.drop_column("schema_mappings", "confirmed_by")
    op.drop_column("schema_mappings", "active")
    op.drop_column("schema_mappings", "mapping_version")
    op.create_unique_constraint(
        "uq_mapping_source_column", "schema_mappings", ["data_source_id", "source_column"]
    )
    op.drop_column("raw_batches", "mapping_snapshot")
    op.drop_column("raw_batches", "schema_version")
    op.alter_column("raw_batches", "storage_uri", existing_type=sa.String(1024), nullable=False)
