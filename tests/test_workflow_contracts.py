from __future__ import annotations

import inspect

from ananhu_agent.schemas import (
    AgentContext,
    IntentResult,
    SafetyResult,
    ToolCallResult,
    VerificationResult,
)
from ananhu_agent.workflow.contracts import (
    SCHEMA_VERSION,
    RunRequest,
    RunStatus,
    StopReason,
    WorkflowPhase,
    WorkflowResult,
    WorkflowState,
)


def test_workflow_phase_sequence_matches_locked_business_flow():
    assert [phase.value for phase in WorkflowPhase] == [
        "understand",
        "merge_facts",
        "validate_facts",
        "clarify",
        "resolve_jurisdiction",
        "plan",
        "execute",
        "validate_evidence",
        "compose",
        "safety",
        "complete",
    ]


def test_run_request_preserves_identity_relationships_from_agent_context():
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=2,
        user_query="四川十级工伤能赔多少？",
    )
    ctx.request.province = "四川省"
    ctx.request.city = "成都市"

    request = RunRequest.from_agent_context(
        ctx,
        run_id="run_1",
        case_id="case_1",
        message_id="msg_1",
    )

    assert request.schema_version == SCHEMA_VERSION
    assert request.run_id == "run_1"
    assert request.request_id == ctx.request.request_id
    assert request.session_id == "sess_1"
    assert request.case_id == "case_1"
    assert request.message_id == "msg_1"
    assert request.turn_id == 2
    assert request.user_query == "四川十级工伤能赔多少？"
    assert request.trusted_jurisdiction == {"province": "四川省", "city": "成都市"}


def test_workflow_state_json_round_trip_and_agent_context_mapping():
    ctx = AgentContext.new_for_query("sess_1", 1, "四川十级工伤，月工资6000")
    ctx.intent_result = IntentResult(
        intent="payment_calculation",
        confidence=0.95,
        slots={"province": "四川省", "disability_grade": 10, "monthly_wage": 6000},
    )
    ctx.conversation.active_slots = dict(ctx.intent_result.slots)
    ctx.tool_results.append(
        ToolCallResult(
            tool_call_id="tool_1",
            tool_name="PaymentCalculationTool",
            called_by="PaymentCalculationAgent",
            tool_status="success",
            tool_error_code=None,
            latency_ms=1,
            input={"disability_grade": 10, "monthly_wage": 6000},
            output={"items": [{"name": "一次性伤残补助金", "amount": 42000}]},
        )
    )
    ctx.verification_result = VerificationResult(passed=True)
    ctx.safety_result = SafetyResult(passed=True)
    ctx.final_answer = "参考答案"

    request = RunRequest.from_agent_context(ctx, run_id="run_1")
    state = WorkflowState.from_agent_context(ctx, request)
    restored = WorkflowState.model_validate_json(state.model_dump_json())

    assert restored.schema_version == SCHEMA_VERSION
    assert restored.run_id == "run_1"
    assert restored.phase is WorkflowPhase.COMPLETE
    assert restored.status is RunStatus.COMPLETED
    assert restored.stop_reason is StopReason.COMPLETE
    assert restored.case_facts["province"] == "四川省"
    assert restored.intent_result["intent"] == "payment_calculation"
    assert restored.capability_results[0]["tool_name"] == "PaymentCalculationTool"
    assert restored.final_answer == "参考答案"


def test_workflow_result_json_round_trip_for_clarification():
    result = WorkflowResult(
        schema_version=SCHEMA_VERSION,
        run_id="run_1",
        request_id="req_1",
        session_id="sess_1",
        status=RunStatus.STOPPED,
        stop_reason=StopReason.NEEDS_CLARIFICATION,
        final_answer=None,
        clarification_question="请补充事故场景。",
    )

    restored = WorkflowResult.model_validate_json(result.model_dump_json())

    assert restored.stop_reason is StopReason.NEEDS_CLARIFICATION
    assert restored.clarification_question == "请补充事故场景。"


def test_workflow_contracts_do_not_import_agent_framework_types():
    source = inspect.getsource(inspect.getmodule(RunRequest))
    import_lines = [
        line
        for line in source.splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    imports = "\n".join(import_lines).lower()

    assert "langgraph" not in imports
    assert "stategraph" not in imports
    assert "command" not in imports
    assert "agno" not in imports
