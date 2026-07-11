from __future__ import annotations

from ananhu_agent.schemas import TraceEvent


def test_trace_event_accepts_runtime_node_attempt_and_logical_call_identity():
    event = TraceEvent.new(
        request_id="req_1",
        session_id="sess_1",
        event_type="capability_finished",
        phase="execute",
        payload={"capability_name": "knowledge.search"},
        runtime_name="native",
        runtime_version="workflow.v1",
        node_id="execute",
        logical_call_id="call_knowledge_search_1",
        attempt=2,
    )

    restored = TraceEvent.model_validate_json(event.model_dump_json())

    assert restored.runtime_name == "native"
    assert restored.runtime_version == "workflow.v1"
    assert restored.node_id == "execute"
    assert restored.logical_call_id == "call_knowledge_search_1"
    assert restored.attempt == 2


def test_trace_event_keeps_backward_compatible_defaults():
    event = TraceEvent.new(
        request_id="req_1",
        session_id="sess_1",
        event_type="request_received",
        phase="orchestrator",
        payload={},
    )

    assert event.runtime_name is None
    assert event.runtime_version is None
    assert event.node_id is None
    assert event.logical_call_id is None
    assert event.attempt is None
