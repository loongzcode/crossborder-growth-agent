"""Initial organization and agent-run persistence models."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from crossborder_domain import WorkflowStatus


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OrganizationModel(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)


class AgentRunModel(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(
            WorkflowStatus,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
            length=32,
        ),
        default=WorkflowStatus.QUEUED,
        nullable=False,
        index=True,
    )
    requested_agents: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    checkpoint_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
