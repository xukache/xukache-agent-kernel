from ananhu_agent.schemas import ToolCallRequest
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.tools.executor import ToolExecutor
from ananhu_agent.tools.registry import ToolDefinition, ToolRegistry


def test_tool_executor_rejects_unregistered_tool(tmp_path):
    executor = ToolExecutor(ToolRegistry(), TraceRecorder(tmp_path / "trace.jsonl"))
    result = executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_0",
            tool_name="UnknownTool",
            called_by="PolicyRAGAgent",
            input={"query": "工伤认定"},
        ),
    )

    assert result.tool_status == "failed"
    assert result.tool_error_code == "tool_not_registered"
    assert executor.trace_recorder.read_all()[0]["event_type"] == "tool_failed"


def test_tool_executor_rejects_disallowed_caller(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            handler=lambda payload: {"documents": []},
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))
    request = ToolCallRequest(
        tool_call_id="tool_1",
        tool_name="PolicyRAGTool",
        called_by="PaymentCalculationAgent",
        input={"query": "工伤认定"},
    )

    result = executor.execute("req_1", "sess_1", request)

    assert result.tool_status == "failed"
    assert result.tool_error_code == "caller_not_allowed"
    assert executor.trace_recorder.read_all()[0]["event_type"] == "tool_failed"


def test_tool_executor_rejects_missing_required_input(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            handler=lambda payload: {"documents": []},
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))

    result = executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_2",
            tool_name="PolicyRAGTool",
            called_by="PolicyRAGAgent",
            input={},
        ),
    )

    assert result.tool_status == "failed"
    assert result.tool_error_code == "invalid_input_schema"


def test_tool_executor_normalizes_handler_exception(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PaymentCalculationTool",
            description="待遇测算",
            risk_level="calculation",
            timeout_ms=3000,
            allowed_callers=["PaymentCalculationAgent"],
            required_input_keys=["monthly_wage"],
            handler=lambda payload: (_ for _ in ()).throw(ValueError("bad wage")),
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))
    result = executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_3",
            tool_name="PaymentCalculationTool",
            called_by="PaymentCalculationAgent",
            input={"monthly_wage": 6000},
        ),
    )

    assert result.tool_status == "failed"
    assert result.tool_error_code == "tool_handler_error"


def test_tool_executor_records_success_trace(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            handler=lambda payload: {"documents": [{"title": payload["query"]}]},
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))

    result = executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_4",
            tool_name="PolicyRAGTool",
            called_by="PolicyRAGAgent",
            input={"query": "工伤认定"},
        ),
    )

    trace = executor.trace_recorder.read_all()[0]
    assert result.tool_status == "success"
    assert result.tool_error_code is None
    assert result.output["documents"] == [{"title": "工伤认定"}]
    assert trace["event_type"] == "tool_finished"
    assert trace["payload"]["tool_status"] == "success"
