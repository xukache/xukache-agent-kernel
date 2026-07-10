from __future__ import annotations

import asyncio
import inspect
from time import sleep

from ananhu_agent.capabilities.contracts import (
    CapabilityIdempotency,
    CapabilityRequest,
    CapabilityStatus,
)
from ananhu_agent.capabilities.tool_executor_gateway import ToolExecutorCapabilityGateway
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.tools.executor import ToolExecutor
from ananhu_agent.tools.payment_calculation import calculate_payment
from ananhu_agent.tools.policy_rag import search_policy
from ananhu_agent.tools.registry import ToolDefinition, ToolRegistry


def _gateway(tmp_path, *, timeout_ms: int = 3000) -> ToolExecutorCapabilityGateway:
    """构造使用真实 ToolExecutor 的能力网关。"""

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索工伤法规、地方政策、办事指南",
            risk_level="read_only",
            timeout_ms=timeout_ms,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            output_required_keys=["documents"],
            handler=search_policy,
        )
    )
    registry.register(
        ToolDefinition(
            name="PaymentCalculationTool",
            description="工伤待遇测算",
            risk_level="calculation",
            timeout_ms=timeout_ms,
            allowed_callers=["PaymentCalculationAgent"],
            required_input_keys=["disability_grade", "monthly_wage"],
            output_required_keys=["items", "assumptions"],
            handler=calculate_payment,
        )
    )
    return ToolExecutorCapabilityGateway(
        ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))
    )


def test_gateway_executes_policy_rag_and_preserves_trace_identity(tmp_path):
    gateway = _gateway(tmp_path)
    request = CapabilityRequest(
        request_id="req_1",
        session_id="sess_1",
        capability_name="PolicyRAGTool",
        caller="PolicyRAGAgent",
        input={"query": "四川 工伤 一次性伤残补助金", "province": "四川省"},
        node_id="execute",
        logical_call_id="call_policy_1",
        attempt=1,
    )

    result = asyncio.run(gateway.execute(request))

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["documents"]
    assert result.tool_call_result["tool_name"] == "PolicyRAGTool"
    assert result.policy.idempotency is CapabilityIdempotency.READ_ONLY_REPEATABLE
    trace_rows = gateway.trace_recorder.read_all()
    assert [row["event_type"] for row in trace_rows] == ["tool_called", "tool_finished"]
    assert trace_rows[-1]["node_id"] == "execute"
    assert trace_rows[-1]["logical_call_id"] == "call_policy_1"
    assert trace_rows[-1]["attempt"] == 1


def test_gateway_executes_payment_calculation(tmp_path):
    gateway = _gateway(tmp_path)
    request = CapabilityRequest(
        request_id="req_1",
        session_id="sess_1",
        capability_name="PaymentCalculationTool",
        caller="PaymentCalculationAgent",
        input={"disability_grade": "十级", "monthly_wage": 6000, "province": "四川省"},
        node_id="execute",
        logical_call_id="call_payment_1",
        attempt=1,
    )

    result = asyncio.run(gateway.execute(request))

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["items"][0]["amount"] == 42000
    assert result.policy.idempotency is CapabilityIdempotency.DETERMINISTIC


def test_gateway_preserves_tool_executor_error_for_illegal_caller(tmp_path):
    gateway = _gateway(tmp_path)
    request = CapabilityRequest(
        request_id="req_1",
        session_id="sess_1",
        capability_name="PolicyRAGTool",
        caller="PaymentCalculationAgent",
        input={"query": "工伤认定"},
        node_id="execute",
        logical_call_id="call_illegal_1",
        attempt=1,
    )

    result = asyncio.run(gateway.execute(request))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "caller_not_allowed"
    assert result.tool_call_result["tool_status"] == "failed"


def test_gateway_preserves_timeout_error(tmp_path):
    def slow_handler(payload):
        sleep(0.05)
        return {"documents": []}

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=1,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            output_required_keys=["documents"],
            handler=slow_handler,
        )
    )
    gateway = ToolExecutorCapabilityGateway(
        ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))
    )
    request = CapabilityRequest(
        request_id="req_1",
        session_id="sess_1",
        capability_name="PolicyRAGTool",
        caller="PolicyRAGAgent",
        input={"query": "工伤认定"},
        node_id="execute",
        logical_call_id="call_timeout_1",
        attempt=1,
    )

    result = asyncio.run(gateway.execute(request))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "tool_timeout"


def test_gateway_reuses_result_for_same_logical_call_id(tmp_path):
    gateway = _gateway(tmp_path)
    request = CapabilityRequest(
        request_id="req_1",
        session_id="sess_1",
        capability_name="PolicyRAGTool",
        caller="PolicyRAGAgent",
        input={"query": "工伤认定"},
        node_id="execute",
        logical_call_id="call_policy_retry",
        attempt=1,
    )

    first = asyncio.run(gateway.execute(request))
    retry = asyncio.run(gateway.execute(request.model_copy(update={"attempt": 2})))

    assert first.status is CapabilityStatus.SUCCESS
    assert retry.status is CapabilityStatus.SUCCESS
    assert retry.reused is True
    assert retry.attempt == 2
    assert retry.logical_call_id == "call_policy_retry"
    assert len([row for row in gateway.trace_recorder.read_all() if row["event_type"] == "tool_finished"]) == 1


def test_gateway_contracts_do_not_import_runtime_frameworks():
    import ananhu_agent.capabilities.contracts as contracts

    source = inspect.getsource(contracts).lower()
    import_lines = [
        line
        for line in source.splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    imports = "\n".join(import_lines)

    assert "langgraph" not in imports
    assert "stategraph" not in imports
    assert "command" not in imports
    assert "agno" not in imports
