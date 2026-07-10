import asyncio

import pytest

from ananhu_agent.ports.model_gateway import ModelErrorCode, ModelGatewayError
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
    assert "model_started" in event_types
    assert "model_finished" in event_types
    assert "model_called" in event_types
    assert "tool_finished" in event_types
    assert "answer_validated" in event_types
    assert "safety_checked" in event_types
    assert "response_ready" in event_types
    model_events = [event for event in events if event["event_type"] == "model_called"]
    assert model_events[0]["payload"]["model_profile"] == "intent_fast"
    assert model_events[0]["payload"]["model_config"]["provider"] == "fake"
    assert model_events[0]["payload"]["model_config"]["model"] == "deterministic-intent"
    lifecycle_events = [
        event for event in events
        if event["event_type"] in {"model_started", "model_finished"}
    ]
    assert {event["run_id"] for event in lifecycle_events} == {"run_vertical"}
    assert {event["logical_call_id"] for event in lifecycle_events} == {
        "run_vertical:understand:model"
    }
    assert TaskStateStore(tmp_path / "task_states.jsonl").read_all()[0]["current_phase"] == "response_ready"
    report = ReportStore(tmp_path / "run_reports.jsonl").read_all()[0]
    assert report["final_intent"] == "payment_calculation"
    assert report["token_usage"]["usage_source"] == "fake"
    assert report["token_usage"]["total_tokens"] == 0


def test_model_gateway_error_is_recorded_in_project_trace(tmp_path):
    class FailingModelGateway:
        async def generate_structured(self, request):
            raise ModelGatewayError(
                ModelErrorCode.RATE_LIMIT,
                "provider rate limited",
                provider="openai_compatible",
                retryable=True,
                status_code=429,
            )

    runtime = create_default_runtime(tmp_path)
    runtime.intent_agent.model_gateway = FailingModelGateway()

    with pytest.raises(ModelGatewayError):
        asyncio.run(runtime.invoke(RunRequest(
            run_id="run_model_failed",
            request_id="req_model_failed",
            session_id="sess_model_failed",
            turn_id=1,
            user_query="工伤认定需要哪些条件？",
            created_at="2026-07-10T00:00:00+08:00",
        )))

    failed = [
        event for event in TraceRecorder(tmp_path / "traces.jsonl").read_all()
        if event["event_type"] == "model_failed"
    ]
    assert failed[0]["payload"] == {
        "model_profile": "intent_fast",
        "provider": "openai_compatible",
        "error_code": "rate_limit_error",
        "retryable": True,
        "status_code": 429,
    }
