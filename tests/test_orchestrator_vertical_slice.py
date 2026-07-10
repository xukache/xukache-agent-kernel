import asyncio

from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.storage.runtime_stores import ReportStore, TaskStateStore, TraceRecorder
from ananhu_agent.workflow.contracts import RunRequest


def test_native_runtime_answers_payment_question_with_trace(tmp_path):
    runtime = create_default_runtime(tmp_path)

    result = asyncio.run(runtime.invoke(RunRequest(
        run_id="run_vertical",
        request_id="req_vertical",
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
        created_at="2026-07-10T00:00:00+08:00",
    )))

    assert result.final_answer is not None
    assert "一次性伤残补助金" in result.final_answer
    assert "42000" in result.final_answer
    assert "以经办机构和正式材料为准" in result.final_answer
    events = TraceRecorder(tmp_path / "traces.jsonl").read_all()
    event_types = [event["event_type"] for event in events]
    assert event_types[0] == "request_received"
    assert "intent_recognized" in event_types
    assert "intent_revised" in event_types
    assert "slots_merged" in event_types
    assert "prompt_built" in event_types
    assert "model_called" in event_types
    assert "tool_finished" in event_types
    assert "answer_validated" in event_types
    assert "safety_checked" in event_types
    assert "response_ready" in event_types
    model_events = [event for event in events if event["event_type"] == "model_called"]
    assert model_events[0]["payload"]["model_profile"] == "intent_fast"
    assert model_events[0]["payload"]["model_config"]["provider"] == "fake"
    assert model_events[0]["payload"]["model_config"]["model"] == "deterministic-intent"
    assert TaskStateStore(tmp_path / "task_states.jsonl").read_all()[0]["current_phase"] == "response_ready"
    assert ReportStore(tmp_path / "run_reports.jsonl").read_all()[0]["final_intent"] == "payment_calculation"
