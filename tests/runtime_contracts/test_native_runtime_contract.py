from __future__ import annotations

import inspect
import asyncio

import pytest

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.cli.tui import presentation
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.capabilities.contracts import (
    CapabilityError,
    CapabilityPolicy,
    CapabilityResult,
    CapabilityStatus,
    CapabilityIdempotency,
)
from ananhu_agent.schemas import SafetyResult
from ananhu_agent.workflow.contracts import (
    RunRequest,
    RunStatus,
    StopReason,
    WorkflowResult,
    WorkflowRuntime,
)


def _request(query: str, *, run_id: str = "run_contract_1") -> RunRequest:
    return RunRequest(
        run_id=run_id,
        request_id=f"req_{run_id}",
        session_id="contract",
        turn_id=1,
        user_query=query,
        created_at="2026-07-10T00:00:00+08:00",
    )


def _runtime(tmp_path, runtime_name: str):
    return create_default_runtime(
        tmp_path,
        RuntimeSettings(runtime_dir=tmp_path, runtime=runtime_name),
    )


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_runtime_invokes_framework_neutral_port_and_returns_result(tmp_path, runtime_name):
    runtime = _runtime(tmp_path, runtime_name)

    assert isinstance(runtime, WorkflowRuntime)
    assert inspect.iscoroutinefunction(runtime.invoke)

    result = asyncio.run(runtime.invoke(_request("四川十级工伤，月工资6000，大概能赔多少钱？")))

    assert isinstance(result, WorkflowResult)
    assert result.status is RunStatus.COMPLETED
    assert result.stop_reason is StopReason.COMPLETE
    assert result.final_answer is not None
    assert "一次性伤残补助金" in result.final_answer
    assert result.final_state is not None
    assert result.final_state.capability_call_count == 2


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_runtime_records_runtime_trace_identity(tmp_path, runtime_name):
    runtime = _runtime(tmp_path, runtime_name)

    asyncio.run(runtime.invoke(_request("四川十级工伤，月工资6000，大概能赔多少钱？")))

    events = runtime.trace_recorder.read_all()
    assert events
    assert {event["runtime_name"] for event in events} == {runtime_name}
    assert all(event["node_id"] for event in events)
    capability_events = [event for event in events if event["event_type"] == "tool_called"]
    assert capability_events
    assert all(event["logical_call_id"] for event in capability_events)
    assert all(event["attempt"] == 1 for event in capability_events)


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_runtime_surfaces_clarification_stop_reason(tmp_path, runtime_name):
    runtime = _runtime(tmp_path, runtime_name)

    result = asyncio.run(runtime.invoke(_request("这个能不能算？", run_id="run_clarify")))

    assert result.status is RunStatus.STOPPED
    assert result.stop_reason is StopReason.NEEDS_CLARIFICATION
    assert result.clarification_question


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_runtime_surfaces_insufficient_evidence_stop_reason(tmp_path, runtime_name):
    runtime = _runtime(tmp_path, runtime_name)

    result = asyncio.run(runtime.invoke(_request("辽宁特殊政策怎么赔？", run_id="run_no_evidence")))

    assert result.status is RunStatus.STOPPED
    assert result.stop_reason is StopReason.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_runtime_surfaces_capability_failed_stop_reason(tmp_path, runtime_name):
    runtime = _runtime(tmp_path, runtime_name)

    async def fail_capability(request):
        return CapabilityResult(
            request_id=request.request_id,
            session_id=request.session_id,
            capability_name=request.capability_name,
            caller=request.caller,
            node_id=request.node_id,
            logical_call_id=request.logical_call_id,
            attempt=request.attempt,
            status=CapabilityStatus.FAILED,
            policy=CapabilityPolicy(
                risk_level="read_only",
                timeout_ms=1,
                idempotency=CapabilityIdempotency.READ_ONLY_REPEATABLE,
            ),
            error=CapabilityError(code="tool_timeout", message="tool_timeout"),
            tool_call_result={
                "tool_call_id": request.logical_call_id,
                "tool_name": request.capability_name,
                "called_by": request.caller,
                "tool_status": "failed",
                "tool_error_code": "tool_timeout",
                "latency_ms": 1,
                "input": request.input,
                "output": {},
                "fallback_used": True,
                "fallback_reason": "tool_timeout",
            },
        )

    runtime.capability_gateway.execute = fail_capability
    result = asyncio.run(runtime.invoke(_request("四川十级工伤，月工资6000，大概能赔多少钱？", run_id="run_cap_fail")))

    assert result.status is RunStatus.FAILED
    assert result.stop_reason is StopReason.CAPABILITY_FAILED


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_runtime_surfaces_safety_blocked_stop_reason(tmp_path, monkeypatch, runtime_name):
    from ananhu_agent.runtimes.native import stages

    class BlockingSafetyGuard:
        def check(self, answer: str) -> SafetyResult:
            return SafetyResult(passed=False, warnings=["absolute_commitment"])

    monkeypatch.setattr(stages, "PolicySafetyGuard", BlockingSafetyGuard)
    runtime = _runtime(tmp_path, runtime_name)

    result = asyncio.run(runtime.invoke(_request("四川十级工伤，月工资6000，大概能赔多少钱？", run_id="run_safe")))

    assert result.status is RunStatus.STOPPED
    assert result.stop_reason is StopReason.SAFETY_BLOCKED


def test_runtime_contracts_do_not_import_langgraph_types():
    source = inspect.getsource(inspect.getmodule(WorkflowRuntime))

    assert "from langgraph" not in source.lower()
    assert "import langgraph" not in source.lower()
    assert "StateGraph" not in source
    assert "Command" not in source


@pytest.mark.parametrize(
    "runtime_scenario",
    [
        pytest.param("clarification", id="clarification"),
        pytest.param("insufficient_evidence", id="insufficient-evidence"),
        pytest.param("capability_failed", id="capability-failed"),
        pytest.param("safety_blocked", id="safety-blocked"),
    ],
)
def test_all_real_runtime_stop_paths_have_visible_messages(tmp_path, monkeypatch, runtime_scenario):
    if runtime_scenario == "clarification":
        result = asyncio.run(_runtime(tmp_path, "native").invoke(_request("这个能不能算？")))
    elif runtime_scenario == "insufficient_evidence":
        result = asyncio.run(_runtime(tmp_path, "native").invoke(_request("辽宁特殊政策怎么赔？")))
    elif runtime_scenario == "capability_failed":
        runtime = _runtime(tmp_path, "native")

        async def fail_capability(request):
            return CapabilityResult(
                request_id=request.request_id,
                session_id=request.session_id,
                capability_name=request.capability_name,
                caller=request.caller,
                node_id=request.node_id,
                logical_call_id=request.logical_call_id,
                attempt=request.attempt,
                status=CapabilityStatus.FAILED,
                policy=CapabilityPolicy(
                    risk_level="read_only",
                    timeout_ms=1,
                    idempotency=CapabilityIdempotency.READ_ONLY_REPEATABLE,
                ),
                error=CapabilityError(code="tool_timeout", message="tool_timeout"),
                tool_call_result={
                    "tool_call_id": request.logical_call_id,
                    "tool_name": request.capability_name,
                    "called_by": request.caller,
                    "tool_status": "failed",
                    "tool_error_code": "tool_timeout",
                    "latency_ms": 1,
                    "input": request.input,
                    "output": {},
                    "fallback_used": True,
                    "fallback_reason": "tool_timeout",
                },
            )

        runtime.capability_gateway.execute = fail_capability
        result = asyncio.run(runtime.invoke(_request("四川十级工伤，月工资6000，大概能赔多少钱？")))
    else:
        from ananhu_agent.runtimes.native import stages

        class BlockingSafetyGuard:
            def check(self, answer: str) -> SafetyResult:
                return SafetyResult(passed=False, warnings=["absolute_commitment"])

        monkeypatch.setattr(stages, "PolicySafetyGuard", BlockingSafetyGuard)
        result = asyncio.run(_runtime(tmp_path, "native").invoke(
            _request("四川十级工伤，月工资6000，大概能赔多少钱？")
        ))

    assert presentation.visible_result_message(result)
