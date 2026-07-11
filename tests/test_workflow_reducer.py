from __future__ import annotations

import inspect

from ananhu_agent.workflow.contracts import (
    RunStatus,
    StatePatch,
    StopReason,
    WorkflowPhase,
    WorkflowState,
)
from ananhu_agent.workflow.reducer import reduce_workflow_state


def _initial_state() -> WorkflowState:
    """构造 reducer 测试使用的最小工作流状态。"""

    return WorkflowState(
        run_id="run_1",
        request_id="req_1",
        session_id="sess_1",
        phase=WorkflowPhase.UNDERSTAND,
    )


def test_reducer_applies_patch_with_overwrite_append_and_business_id_merge_rules():
    state = _initial_state()
    patch = StatePatch(
        patch_id="patch_1",
        run_id="run_1",
        source_phase=WorkflowPhase.UNDERSTAND,
        next_phase=WorkflowPhase.MERGE_FACTS,
        node_id="understand",
        logical_call_id="call_understand_1",
        attempt=1,
        fact_updates={"province": "四川省", "monthly_wage": 6000},
        intent_result={"intent": "payment_calculation", "confidence": 0.9},
        capability_results=[
            {
                "logical_call_id": "call_1",
                "capability_name": "payment.calculate",
                "status": "success",
                "output": {"amount": 42000},
            }
        ],
        evidence=[
            {
                "evidence_id": "ev_1",
                "source": "knowledge.search",
                "title": "工伤保险条例",
            }
        ],
    )

    result = reduce_workflow_state(state, patch)

    assert result.ok is True
    assert result.applied is True
    assert result.state.phase is WorkflowPhase.MERGE_FACTS
    assert result.state.case_facts["province"] == "四川省"
    assert result.state.intent_result["intent"] == "payment_calculation"
    assert result.state.capability_results[0]["logical_call_id"] == "call_1"
    assert result.state.evidence[0]["evidence_id"] == "ev_1"
    assert result.state.applied_patch_ids == ["patch_1"]


def test_reducer_ignores_duplicate_patch_id_without_duplicate_appends():
    state = _initial_state()
    patch = StatePatch(
        patch_id="patch_1",
        run_id="run_1",
        source_phase=WorkflowPhase.UNDERSTAND,
        next_phase=WorkflowPhase.MERGE_FACTS,
        node_id="understand",
        logical_call_id="call_understand_1",
        attempt=1,
        capability_results=[
            {"logical_call_id": "call_1", "capability_name": "knowledge.search"}
        ],
        evidence=[{"evidence_id": "ev_1", "source": "knowledge.search"}],
    )

    first = reduce_workflow_state(state, patch)
    second = reduce_workflow_state(first.state, patch)

    assert first.applied is True
    assert second.ok is True
    assert second.applied is False
    assert second.error_code is None
    assert second.state.capability_results == [
        {"logical_call_id": "call_1", "capability_name": "knowledge.search"}
    ]
    assert second.state.evidence == [{"evidence_id": "ev_1", "source": "knowledge.search"}]
    assert second.state.applied_patch_ids == ["patch_1"]


def test_reducer_returns_structured_failure_for_illegal_phase_transition():
    state = _initial_state()
    patch = StatePatch(
        patch_id="patch_bad",
        run_id="run_1",
        source_phase=WorkflowPhase.UNDERSTAND,
        next_phase=WorkflowPhase.COMPLETE,
        node_id="understand",
        logical_call_id="call_understand_1",
        attempt=1,
    )

    result = reduce_workflow_state(state, patch)

    assert result.ok is False
    assert result.applied is False
    assert result.error_code == "invalid_phase_transition"
    assert "understand -> complete" in result.error_message
    assert result.state.phase is WorkflowPhase.UNDERSTAND


def test_reducer_validates_source_phase_and_run_id():
    state = _initial_state()
    patch = StatePatch(
        patch_id="patch_wrong_run",
        run_id="run_other",
        source_phase=WorkflowPhase.UNDERSTAND,
        next_phase=WorkflowPhase.MERGE_FACTS,
        node_id="understand",
        logical_call_id="call_understand_1",
        attempt=1,
    )

    result = reduce_workflow_state(state, patch)

    assert result.ok is False
    assert result.error_code == "run_id_mismatch"


def test_reducer_contracts_do_not_import_agent_framework_types():
    reducer_source = inspect.getsource(reduce_workflow_state)
    patch_source = inspect.getsource(StatePatch)
    source = f"{reducer_source}\n{patch_source}".lower()

    assert "langgraph" not in source
    assert "stategraph" not in source
    assert "command" not in source
    assert "agno" not in source


def test_patch_can_complete_state_with_final_result_fields():
    state = WorkflowState(
        run_id="run_1",
        request_id="req_1",
        session_id="sess_1",
        phase=WorkflowPhase.SAFETY,
    )
    patch = StatePatch(
        patch_id="patch_complete",
        run_id="run_1",
        source_phase=WorkflowPhase.SAFETY,
        next_phase=WorkflowPhase.COMPLETE,
        node_id="safety",
        logical_call_id="call_safety_1",
        attempt=1,
        status=RunStatus.COMPLETED,
        stop_reason=StopReason.COMPLETE,
        final_answer="结论：仅供参考。",
    )

    result = reduce_workflow_state(state, patch)

    assert result.ok is True
    assert result.state.status is RunStatus.COMPLETED
    assert result.state.stop_reason is StopReason.COMPLETE
    assert result.state.final_answer == "结论：仅供参考。"
