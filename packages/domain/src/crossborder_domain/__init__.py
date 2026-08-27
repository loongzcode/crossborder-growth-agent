"""Domain contracts shared by API, agents, tools, and evaluation."""

from crossborder_domain.agents import (
    AgentName,
    AgentRequest,
    AgentResult,
    AgentResultStatus,
    EvidenceReference,
    RecommendedAction,
    RiskFinding,
    RiskSeverity,
    WorkflowStatus,
)
from crossborder_domain.common import Money, TimeRange
from crossborder_domain.data import (
    AdvertisingIngestionPreview,
    AdvertisingRecord,
    ColumnMapping,
    DataDomain,
    DataQualityIssue,
    MappingStatus,
    QualitySeverity,
)

__all__ = [
    "AdvertisingIngestionPreview",
    "AdvertisingRecord",
    "AgentName",
    "AgentRequest",
    "AgentResult",
    "AgentResultStatus",
    "ColumnMapping",
    "DataDomain",
    "DataQualityIssue",
    "EvidenceReference",
    "MappingStatus",
    "Money",
    "QualitySeverity",
    "RecommendedAction",
    "RiskFinding",
    "RiskSeverity",
    "TimeRange",
    "WorkflowStatus",
]
