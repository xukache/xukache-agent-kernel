from ananhu_agent.schemas import RunReport, TaskState, TraceEvent
from ananhu_agent.storage.runtime_stores import ReportStore, TaskStateStore, TraceRecorder


def test_trace_recorder_appends_jsonl(tmp_path):
    recorder = TraceRecorder(tmp_path / "traces.jsonl")
    event = TraceEvent.new(
        request_id="req_1",
        session_id="sess_1",
        event_type="request_received",
        phase="orchestrator",
        payload={"user_query": "上班路上交通事故算工伤吗？"},
    )

    recorder.record(event)
    rows = recorder.read_all()

    assert len(rows) == 1
    assert rows[0]["event_type"] == "request_received"
    assert rows[0]["payload"]["user_query"] == "上班路上交通事故算工伤吗？"


def test_task_state_and_report_store_append_runtime_evidence(tmp_path):
    task_store = TaskStateStore(tmp_path / "task_states.jsonl")
    report_store = ReportStore(tmp_path / "run_reports.jsonl")
    task_store.append(
        TaskState(
            id="state_1",
            session_id="sess_1",
            turn_id=1,
            user_query="劳动能力鉴定需要准备哪些材料？",
            status="completed",
            current_phase="response_ready",
        )
    )
    report_store.append(
        RunReport(
            id="report_1",
            session_id="sess_1",
            final_status="success",
            final_intent="labor_capacity",
            route_agents=["DomainConsultationAgent", "PolicyRAGAgent"],
            tool_count=1,
            model_attempts=1,
            prompt_refs=["intent_router.v1"],
            prompt_metadata={},
            output_schema_valid_rate=1.0,
            token_usage={},
            latency_ms=8,
            fallback_used=False,
            safety_result={"passed": True},
            badcase_candidate=False,
        )
    )

    assert task_store.read_all()[0]["current_phase"] == "response_ready"
    assert report_store.read_all()[0]["final_intent"] == "labor_capacity"
