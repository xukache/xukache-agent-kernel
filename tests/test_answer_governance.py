from ananhu_agent.capabilities.contracts import (
    CapabilityIdempotency,
    CapabilityPolicy,
    CapabilityResult,
    CapabilityStatus,
)
from ananhu_agent.orchestrator.aggregator import build_final_answer
from ananhu_agent.orchestrator.safety import PolicySafetyGuard
from ananhu_agent.orchestrator.validators import AnswerValidator
from ananhu_agent.schemas import AgentContext


def test_final_answer_includes_citation_and_risk_note():
    ctx = AgentContext.new_for_query("sess_1", 1, "上班路上交通事故算工伤吗？")
    ctx.capability_results.append(
        CapabilityResult(
            request_id=ctx.request.request_id,
            session_id=ctx.request.session_id,
            capability_name="knowledge.search",
            caller="PolicyRAGAgent",
            node_id="execute",
            logical_call_id="call_1",
            attempt=1,
            status=CapabilityStatus.SUCCESS,
            policy=CapabilityPolicy(
                risk_level="read_only",
                timeout_ms=3000,
                idempotency=CapabilityIdempotency.READ_ONLY_REPEATABLE,
            ),
            output={
                "evidences": [
                    {
                        "content": "上下班途中非本人主要责任交通事故应认定为工伤。",
                        "citation": {
                            "title": "工伤保险条例",
                            "article": "第十四条",
                            "source_url": "https://example.com/policy",
                            "document_version": "v1",
                            "evidence_id": "ev_1",
                            "province": "四川省",
                            "city": "",
                        },
                    }
                ]
            },
        )
    )

    answer = build_final_answer(ctx)

    assert "工伤保险条例" in answer
    assert "以经办机构和正式材料为准" in answer


def test_validator_rejects_answer_without_citation():
    result = AnswerValidator().validate("这个一定算工伤。", citations=[])

    assert result.passed is False
    assert "missing_citation" in result.issues


def test_safety_guard_rejects_absolute_commitment():
    result = PolicySafetyGuard().check("你这个一定能认定工伤。")

    assert result.passed is False
