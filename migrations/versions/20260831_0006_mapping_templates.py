"""增加组织级列映射模板和版本记录。

Revision ID: 20260831_0006
Revises: 20260831_0005
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0006"
down_revision: str | None = "20260831_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mapping_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("mappings", sa.JSON(), nullable=False),
        sa.Column("mapping_signature", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["system_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "data_source_id",
            "name",
            "version",
            name="uq_mapping_template_source_name_version",
        ),
    )
    op.create_index(
        "ix_mapping_templates_organization_id", "mapping_templates", ["organization_id"]
    )
    op.create_index("ix_mapping_templates_data_source_id", "mapping_templates", ["data_source_id"])
    op.create_index("ix_mapping_templates_domain", "mapping_templates", ["domain"])
    op.create_index("ix_mapping_templates_active", "mapping_templates", ["active"])


def downgrade() -> None:
    op.drop_index("ix_mapping_templates_active", table_name="mapping_templates")
    op.drop_index("ix_mapping_templates_domain", table_name="mapping_templates")
    op.drop_index("ix_mapping_templates_data_source_id", table_name="mapping_templates")
    op.drop_index("ix_mapping_templates_organization_id", table_name="mapping_templates")
    op.drop_table("mapping_templates")
