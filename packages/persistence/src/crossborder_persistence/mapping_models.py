"""Organization-scoped reusable ingestion mapping templates."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from crossborder_domain import DataDomain
from crossborder_persistence.models import Base, TimestampMixin


class MappingTemplateModel(TimestampMixin, Base):
    __tablename__ = "mapping_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "data_source_id",
            "name",
            "version",
            name="uq_mapping_template_source_name_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[DataDomain] = mapped_column(
        Enum(
            DataDomain,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    mappings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    mapping_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("system_users.id", ondelete="SET NULL"), nullable=True
    )
