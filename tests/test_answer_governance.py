from ananhu_agent.orchestrator.aggregator import build_final_answer
from ananhu_agent.orchestrator.safety import PolicySafetyGuard
from ananhu_agent.orchestrator.validators import AnswerValidator
from ananhu_agent.schemas import AgentContext, ToolCallResult


def test_final_answer_includes_citation_and_risk_note():
    ctx = AgentContext.new_for_query("sess_1", 1, "上班路上交通事故算工伤吗？")
    ctx.tool_results.append(
        ToolCallResult(
            tool_call_id="tool_1",
            tool_name="PolicyRAGTool",
            called_by="DomainConsultationAgent",
            tool_status="success",
            tool_error_code=None,
            latency_ms=1,
            input={},
            output={
                "documents": [
                    {
                        "content": "上下班途中非本人主要责任交通事故应认定为工伤。",
                        "citation": {"title": "工伤保险条例", "article": "第十四条"},
                    }
                ]
            },
            fallback_used=False,
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
