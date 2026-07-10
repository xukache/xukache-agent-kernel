from __future__ import annotations

from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator
from ananhu_agent.schemas import (
    AgentContext,
    AgentMessage,
    IntentResult,
    SafetyResult,
    ToolCallResult,
    VerificationResult,
)
from ananhu_agent.workflow.contracts import (
    RunRequest,
    RunStatus,
    StopReason,
    WorkflowPhase,
    WorkflowState,
)


def _state_from_context(ctx: AgentContext) -> WorkflowState:
    """把测试构造的旧上下文映射成任务 26 的框架中立状态。"""

    return WorkflowState.from_agent_context(
        ctx,
        RunRequest.from_agent_context(ctx, run_id="run_characterization"),
    )


def test_characterizes_completed_orchestrator_run(tmp_path):
    orchestrator = create_default_orchestrator(tmp_path)

    ctx = orchestrator.ask("sess_1", 1, "四川十级工伤，月工资6000，大概能赔多少钱？")
    state = _state_from_context(ctx)

    assert state.status is RunStatus.COMPLETED
    assert state.stop_reason is StopReason.COMPLETE
    assert state.phase is WorkflowPhase.COMPLETE
    assert state.final_answer is not None
    assert state.capability_call_count == 2


def test_characterizes_clarification_required_context():
    ctx = AgentContext.new_for_query("sess_1", 1, "这个能不能算？")
    ctx.intent_result = IntentResult(
        intent="work_injury_recognition",
        confidence=0.4,
        missing_slots=["accident_type"],
        ask_clarification="请补充事故场景、发生时间、地区和责任划分。",
    )
    ctx.agent_outputs.append(
        AgentMessage(
            agent_name="IntentRouterAgent",
            status="need_clarification",
            content="需要补充信息",
            missing_slots=["accident_type"],
        )
    )

    state = _state_from_context(ctx)

    assert state.status is RunStatus.STOPPED
    assert state.stop_reason is StopReason.NEEDS_CLARIFICATION
    assert state.phase is WorkflowPhase.CLARIFY
    assert state.clarification_question == "请补充事故场景、发生时间、地区和责任划分。"


def test_characterizes_insufficient_evidence_context():
    ctx = AgentContext.new_for_query("sess_1", 1, "辽宁特殊政策怎么赔？")
    ctx.intent_result = IntentResult(intent="policy_consultation", confidence=0.8)
    ctx.tool_results.append(
        ToolCallResult(
            tool_call_id="tool_1",
            tool_name="PolicyRAGTool",
            called_by="PolicyRAGAgent",
            tool_status="success",
            tool_error_code=None,
            latency_ms=1,
            input={"query": "辽宁特殊政策"},
            output={"documents": []},
        )
    )
    ctx.final_answer = "当前没有检索到可引用的结构化政策依据。"
    ctx.verification_result = VerificationResult(passed=False, issues=["missing_citation"])
    ctx.safety_result = SafetyResult(passed=True)

    state = _state_from_context(ctx)

    assert state.status is RunStatus.STOPPED
    assert state.stop_reason is StopReason.INSUFFICIENT_EVIDENCE
    assert state.phase is WorkflowPhase.VALIDATE_EVIDENCE


def test_characterizes_capability_failure_context():
    ctx = AgentContext.new_for_query("sess_1", 1, "四川工伤待遇")
    ctx.tool_results.append(
        ToolCallResult(
            tool_call_id="tool_1",
            tool_name="PolicyRAGTool",
            called_by="PolicyRAGAgent",
            tool_status="failed",
            tool_error_code="tool_timeout",
            latency_ms=3000,
            input={"query": "四川工伤待遇"},
            output={},
        )
    )

    state = _state_from_context(ctx)

    assert state.status is RunStatus.FAILED
    assert state.stop_reason is StopReason.CAPABILITY_FAILED
    assert state.phase is WorkflowPhase.EXECUTE


def test_characterizes_safety_blocked_context():
    ctx = AgentContext.new_for_query("sess_1", 1, "十级工伤一定赔多少钱？")
    ctx.final_answer = "一定能赔 42000 元。"
    ctx.verification_result = VerificationResult(passed=True)
    ctx.safety_result = SafetyResult(passed=False, warnings=["absolute_commitment"])

    state = _state_from_context(ctx)

    assert state.status is RunStatus.STOPPED
    assert state.stop_reason is StopReason.SAFETY_BLOCKED
    assert state.phase is WorkflowPhase.SAFETY
