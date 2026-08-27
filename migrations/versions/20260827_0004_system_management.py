"""建立系统管理、身份认证与 RBAC 表。

Revision ID: 20260827_0004
Revises: 20260827_0003
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0004"
down_revision: str | None = "20260827_0003"
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


def upgrade() -> None:
    op.create_table(
        "system_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_system_role_org_code"),
    )
    op.create_index("ix_system_roles_organization_id", "system_roles", ["organization_id"])
    op.create_index("ix_system_roles_enabled", "system_roles", ["enabled"])

    op.create_table(
        "system_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("nickname", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("gender", sa.String(length=16), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "username", name="uq_system_user_org_username"),
        sa.UniqueConstraint("organization_id", "email", name="uq_system_user_org_email"),
    )
    op.create_index("ix_system_users_organization_id", "system_users", ["organization_id"])
    op.create_index("ix_system_users_username", "system_users", ["username"])
    op.create_index("ix_system_users_email", "system_users", ["email"])
    op.create_index("ix_system_users_enabled", "system_users", ["enabled"])

    op.create_table(
        "system_menus",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("path", sa.String(length=300), nullable=False),
        sa.Column("component", sa.String(length=300), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("hidden", sa.Boolean(), nullable=False),
        sa.Column("hide_tab", sa.Boolean(), nullable=False),
        sa.Column("keep_alive", sa.Boolean(), nullable=False),
        sa.Column("fixed_tab", sa.Boolean(), nullable=False),
        sa.Column("full_page", sa.Boolean(), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=False),
        sa.Column("iframe", sa.Boolean(), nullable=False),
        sa.Column("active_path", sa.String(length=300), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["parent_id"], ["system_menus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_system_menu_name"),
    )
    op.create_index("ix_system_menus_parent_id", "system_menus", ["parent_id"])
    op.create_index("ix_system_menus_sort", "system_menus", ["sort"])
    op.create_index("ix_system_menus_enabled", "system_menus", ["enabled"])

    op.create_table(
        "system_permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("menu_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["menu_id"], ["system_menus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("menu_id", "code", name="uq_system_permission_menu_code"),
    )
    op.create_index("ix_system_permissions_menu_id", "system_permissions", ["menu_id"])
    op.create_index("ix_system_permissions_code", "system_permissions", ["code"])

    op.create_table(
        "user_role_assignments",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["system_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["system_roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.create_table(
        "role_menu_assignments",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("menu_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["system_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["menu_id"], ["system_menus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "menu_id"),
    )
    op.create_table(
        "role_permission_assignments",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["system_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["system_permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )


def downgrade() -> None:
    op.drop_table("role_permission_assignments")
    op.drop_table("role_menu_assignments")
    op.drop_table("user_role_assignments")
    op.drop_index("ix_system_permissions_code", table_name="system_permissions")
    op.drop_index("ix_system_permissions_menu_id", table_name="system_permissions")
    op.drop_table("system_permissions")
    op.drop_index("ix_system_menus_enabled", table_name="system_menus")
    op.drop_index("ix_system_menus_sort", table_name="system_menus")
    op.drop_index("ix_system_menus_parent_id", table_name="system_menus")
    op.drop_table("system_menus")
    op.drop_index("ix_system_users_enabled", table_name="system_users")
    op.drop_index("ix_system_users_email", table_name="system_users")
    op.drop_index("ix_system_users_username", table_name="system_users")
    op.drop_index("ix_system_users_organization_id", table_name="system_users")
    op.drop_table("system_users")
    op.drop_index("ix_system_roles_enabled", table_name="system_roles")
    op.drop_index("ix_system_roles_organization_id", table_name="system_roles")
    op.drop_table("system_roles")
