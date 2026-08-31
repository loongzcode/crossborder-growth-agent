"""完善组织级数据源管理和连接状态字段。

Revision ID: 20260831_0005
Revises: 20260827_0004
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0005"
down_revision: str | None = "20260827_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("data_sources", sa.Column("credentials_encrypted", sa.Text(), nullable=True))
    op.add_column(
        "data_sources",
        sa.Column(
            "connection_status",
            sa.String(length=32),
            server_default="untested",
            nullable=False,
        ),
    )
    op.add_column(
        "data_sources", sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("data_sources", sa.Column("last_error_code", sa.String(length=64), nullable=True))
    op.add_column(
        "data_sources", sa.Column("last_error_message", sa.String(length=500), nullable=True)
    )
    op.create_unique_constraint(
        "uq_data_source_org_name", "data_sources", ["organization_id", "name"]
    )
    op.create_index("ix_data_sources_connection_status", "data_sources", ["connection_status"])


def downgrade() -> None:
    op.drop_index("ix_data_sources_connection_status", table_name="data_sources")
    op.drop_constraint("uq_data_source_org_name", "data_sources", type_="unique")
    op.drop_column("data_sources", "last_error_message")
    op.drop_column("data_sources", "last_error_code")
    op.drop_column("data_sources", "last_tested_at")
    op.drop_column("data_sources", "connection_status")
    op.drop_column("data_sources", "credentials_encrypted")
