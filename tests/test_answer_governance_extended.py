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


def test_validator_rejects_region_mismatch():
    result = AnswerValidator().validate(
        "依据四川省政策处理。",
        citations=[
            {"title": "四川省工伤保险条例实施办法", "article": "待遇章节", "province": "四川省"}
        ],
        expected_region={"province": "辽宁省"},
    )

    assert result.passed is False
    assert "region_mismatch" in result.issues


def test_safety_guard_rejects_medical_grade_commitment():
    result = PolicySafetyGuard().check("你的伤情肯定可以评为十级伤残。")

    assert result.passed is False
    assert "medical_grade_commitment" in result.warnings


def test_aggregator_uses_conservative_answer_without_citations():
    ctx = AgentContext.new_for_query("sess_1", 1, "大概赔多少钱？")
    ctx.capability_results.append(
        CapabilityResult(
            request_id=ctx.request.request_id,
            session_id=ctx.request.session_id,
            capability_name="payment.calculate",
            caller="PaymentCalculationAgent",
            node_id="execute",
            logical_call_id="call_1",
            attempt=1,
            status=CapabilityStatus.SUCCESS,
            policy=CapabilityPolicy(
                risk_level="calculation",
                timeout_ms=3000,
                idempotency=CapabilityIdempotency.DETERMINISTIC,
            ),
            output={"items": [{"name": "一次性伤残补助金", "amount": 42000, "formula": "6000 * 7"}]},
        )
    )

    answer = build_final_answer(ctx)

    assert "不能给出确定结论" in answer
    assert "不能作为待遇承诺" in answer


def test_safety_guard_rejects_precise_amount_commitment():
    result = PolicySafetyGuard().check("你的情况肯定赔42000元。")

    assert result.passed is False
    assert "precise_amount_commitment" in result.warnings
