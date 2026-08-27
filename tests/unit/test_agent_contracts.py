from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from crossborder_domain import (
    AgentName,
    AgentRequest,
    AgentResult,
    AgentResultStatus,
    EvidenceReference,
    RecommendedAction,
    RiskFinding,
    RiskSeverity,
)
from crossborder_domain.agents import ActionImpact


def test_all_nine_agents_have_stable_identifiers() -> None:
    assert {agent.value for agent in AgentName} == {
        "supervisor",
        "data_governance",
        "ad_performance",
        "product_intelligence",
        "customer_insight",
        "creative_intelligence",
        "profit_supply",
        "compliance_risk",
        "business_decision",
    }


def test_agent_result_links_actions_and_risks_to_evidence() -> None:
    run_id = uuid4()
    evidence = EvidenceReference(
        source_type="metric_snapshot",
        source_id="campaign:demo:2026-08-27",
        title="广告组日指标",
        captured_at=datetime.now(UTC),
        fields={"spend": 217.81, "orders": 30},
    )

    result = AgentResult(
        run_id=run_id,
        agent=AgentName.AD_PERFORMANCE,
        status=AgentResultStatus.SUCCESS,
        summary="订单成本较观察窗口上升，需要进一步检查素材和库存。",
        confidence=0.82,
        evidence=[evidence],
        risks=[
            RiskFinding(
                code="ADS_COST_RISE",
                title="获客成本上升",
                severity=RiskSeverity.MEDIUM,
                detail="结论来自指标快照，尚未形成预算调整动作。",
                evidence_ids=[evidence.evidence_id],
            )
        ],
        actions=[
            RecommendedAction(
                action_type="review_budget",
                title="复核预算分配",
                rationale="先确认利润和库存约束，再提交预算方案。",
                impact=ActionImpact.HIGH,
                requires_approval=True,
                evidence_ids=[evidence.evidence_id],
            )
        ],
    )

    assert result.actions[0].requires_approval is True
    assert result.actions[0].evidence_ids == [result.evidence[0].evidence_id]


def test_agent_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AgentRequest(
            organization_id=uuid4(),
            objective="诊断昨日广告异常",
            unsupported_field="not allowed",  # type: ignore[call-arg]
        )
