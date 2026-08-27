"""Strict contracts for the supervisor and eight domain agents."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from crossborder_domain.common import StrictDomainModel


class AgentName(StrEnum):
    SUPERVISOR = "supervisor"
    DATA_GOVERNANCE = "data_governance"
    AD_PERFORMANCE = "ad_performance"
    PRODUCT_INTELLIGENCE = "product_intelligence"
    CUSTOMER_INSIGHT = "customer_insight"
    CREATIVE_INTELLIGENCE = "creative_intelligence"
    PROFIT_SUPPLY = "profit_supply"
    COMPLIANCE_RISK = "compliance_risk"
    BUSINESS_DECISION = "business_decision"


class WorkflowStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_DATA = "waiting_for_data"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentResultStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionImpact(StrEnum):
    READ_ONLY = "read_only"
    LOW = "low"
    HIGH = "high"


class EvidenceReference(StrictDomainModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=256)
    captured_at: datetime
    fields: dict[str, Any] = Field(default_factory=dict)


class RiskFinding(StrictDomainModel):
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    severity: RiskSeverity
    detail: str = Field(min_length=1)
    requires_human_review: bool = False
    evidence_ids: list[UUID] = Field(default_factory=list)


class RecommendedAction(StrictDomainModel):
    action_type: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    rationale: str = Field(min_length=1)
    impact: ActionImpact = ActionImpact.READ_ONLY
    requires_approval: bool = False
    owner_role: str | None = Field(default=None, max_length=64)
    evidence_ids: list[UUID] = Field(default_factory=list)


class AgentRequest(StrictDomainModel):
    run_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    objective: str = Field(min_length=3, max_length=4000)
    actor_id: UUID | None = None
    requested_agents: list[AgentName] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResult(StrictDomainModel):
    run_id: UUID
    agent: AgentName
    status: AgentResultStatus
    summary: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    risks: list[RiskFinding] = Field(default_factory=list)
    actions: list[RecommendedAction] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    error_code: str | None = Field(default=None, max_length=64)
