"""Organization-scoped identity, role, menu, and permission models."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crossborder_persistence.models import Base, TimestampMixin

user_role_assignments = Table(
    "user_role_assignments",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("system_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("system_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

role_menu_assignments = Table(
    "role_menu_assignments",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("system_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "menu_id",
        ForeignKey("system_menus.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

role_permission_assignments = Table(
    "role_permission_assignments",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("system_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        ForeignKey("system_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class SystemRoleModel(TimestampMixin, Base):
    __tablename__ = "system_roles"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_system_role_org_code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    menus: Mapped[list["SystemMenuModel"]] = relationship(
        secondary=role_menu_assignments, lazy="selectin"
    )
    permissions: Mapped[list["SystemPermissionModel"]] = relationship(
        secondary=role_permission_assignments, lazy="selectin"
    )


class SystemUserModel(TimestampMixin, Base):
    __tablename__ = "system_users"
    __table_args__ = (
        UniqueConstraint("organization_id", "username", name="uq_system_user_org_username"),
        UniqueConstraint("organization_id", "email", name="uq_system_user_org_email"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    gender: Mapped[str] = mapped_column(String(16), default="保密", nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list[SystemRoleModel]] = relationship(
        secondary=user_role_assignments, lazy="selectin"
    )


class SystemMenuModel(TimestampMixin, Base):
    __tablename__ = "system_menus"
    __table_args__ = (UniqueConstraint("name", name="uq_system_menu_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("system_menus.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(300), nullable=False)
    component: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hide_tab: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    keep_alive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fixed_tab: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_page: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    link: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    iframe: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active_path: Mapped[str] = mapped_column(String(300), default="", nullable=False)

    permissions: Mapped[list["SystemPermissionModel"]] = relationship(
        back_populates="menu", cascade="all, delete-orphan", lazy="selectin"
    )


class SystemPermissionModel(TimestampMixin, Base):
    __tablename__ = "system_permissions"
    __table_args__ = (UniqueConstraint("menu_id", "code", name="uq_system_permission_menu_code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    menu_id: Mapped[UUID] = mapped_column(
        ForeignKey("system_menus.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    menu: Mapped[SystemMenuModel] = relationship(back_populates="permissions")
