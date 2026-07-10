from __future__ import annotations

import asyncio

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.evaluation.differential import RuntimeDifferentialRunner, _events_for_request
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.workflow.contracts import RunRequest, WorkflowRuntime


def _request(query: str, *, suffix: str = "1") -> RunRequest:
    return RunRequest(
        run_id=f"run_diff_{suffix}",
        request_id=f"req_diff_{suffix}",
        session_id="diff",
        turn_id=1,
        user_query=query,
        created_at="2026-07-10T00:00:00+08:00",
    )


def _runner(tmp_path, langgraph_runtime: WorkflowRuntime | None = None):
    native_dir = tmp_path / "native"
    langgraph_dir = tmp_path / "langgraph"
    native = create_default_runtime(
        native_dir,
        RuntimeSettings(runtime_dir=native_dir, runtime="native"),
    )
    langgraph = langgraph_runtime or create_default_runtime(
        langgraph_dir,
        RuntimeSettings(runtime_dir=langgraph_dir, runtime="langgraph"),
    )
    return RuntimeDifferentialRunner(
        native_runtime=native,
        langgraph_runtime=langgraph,
        native_trace=TraceRecorder(native_dir / "traces.jsonl"),
        langgraph_trace=TraceRecorder(langgraph_dir / "traces.jsonl"),
        artifact_path=tmp_path / "runtime-differential.json",
    )


def test_differential_runner_accepts_only_allowed_runtime_differences(tmp_path):
    comparison = asyncio.run(
        _runner(tmp_path).compare(
            _request("四川十级工伤，月工资6000，大概能赔多少钱？"),
            case_id="payment",
        )
    )

    assert comparison.equivalent is True
    assert comparison.mismatches == []
    assert comparison.compared_trace_events > 0


def test_differential_runner_reports_business_state_difference(tmp_path):
    langgraph_dir = tmp_path / "mutated-langgraph"
    actual = create_default_runtime(
        langgraph_dir,
        RuntimeSettings(runtime_dir=langgraph_dir, runtime="langgraph"),
    )

    class MutatingRuntime(WorkflowRuntime):
        async def invoke(self, request: RunRequest):
            result = await actual.invoke(request)
            assert result.final_state is not None
            state = result.final_state.model_copy(deep=True)
            state.case_facts["province"] = "错误地区"
            return result.model_copy(update={"final_state": state}, deep=True)

    comparison = asyncio.run(
        _runner(tmp_path, MutatingRuntime()).compare(
            _request("四川十级工伤，月工资6000，大概能赔多少钱？", suffix="mismatch"),
            case_id="mismatch",
        )
    )

    assert comparison.equivalent is False
    assert any("case_facts.province" in mismatch.path for mismatch in comparison.mismatches)


def test_differential_runner_writes_dataset_artifact(tmp_path):
    report = _runner(tmp_path).run_cases(
        [
            {"id": "case_1", "query": "四川十级工伤，月工资6000，大概能赔多少钱？"},
            {"id": "case_2", "query": "这个能不能算？"},
        ]
    )

    assert report.total == 2
    assert report.equivalent == 2
    assert report.different == 0
    assert (tmp_path / "runtime-differential.json").exists()


def test_trace_normalization_preserves_business_document_id(tmp_path):
    recorder = TraceRecorder(tmp_path / "traces.jsonl")
    recorder.record(
        {
            "id": "trace_random",
            "request_id": "req_1",
            "session_id": "diff",
            "event_type": "tool_finished",
            "phase": "tool",
            "runtime_name": "native",
            "runtime_version": "native.v1",
            "node_id": "execute",
            "logical_call_id": "call_1",
            "attempt": 1,
            "payload": {"document": {"id": "policy_001"}},
            "latency_ms": 1,
            "created_at": "2026-07-10T00:00:00+08:00",
        }
    )

    events = _events_for_request(recorder, "req_1")

    assert "id" not in events[0]
    assert events[0]["payload"]["document"]["id"] == "policy_001"


def test_repeated_dataset_run_does_not_compare_historical_trace_events(tmp_path):
    runner = _runner(tmp_path)
    cases = [{"id": "case_1", "query": "四川十级工伤，月工资6000，大概能赔多少钱？"}]

    first = runner.run_cases(cases)
    second = runner.run_cases(cases)

    assert second.cases[0].request_id != first.cases[0].request_id
    assert second.cases[0].compared_trace_events == first.cases[0].compared_trace_events
