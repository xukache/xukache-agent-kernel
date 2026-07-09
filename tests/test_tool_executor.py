from time import sleep

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
    event_types = [event["event_type"] for event in executor.trace_recorder.read_all()]
    assert event_types == ["tool_called", "tool_failed"]
    assert result.fallback_reason == "tool_not_registered"


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
    event_types = [event["event_type"] for event in executor.trace_recorder.read_all()]
    assert event_types == ["tool_called", "tool_failed"]


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

    trace_events = executor.trace_recorder.read_all()
    assert result.tool_status == "success"
    assert result.tool_error_code is None
    assert result.output["documents"] == [{"title": "工伤认定"}]
    assert [event["event_type"] for event in trace_events] == ["tool_called", "tool_finished"]
    assert trace_events[-1]["payload"]["tool_status"] == "success"


def test_tool_executor_records_tool_called_before_success(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            output_required_keys=["documents"],
            handler=lambda payload: {"documents": []},
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))

    executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_1",
            tool_name="PolicyRAGTool",
            called_by="PolicyRAGAgent",
            input={"query": "工伤认定"},
        ),
    )

    event_types = [event["event_type"] for event in executor.trace_recorder.read_all()]
    assert event_types == ["tool_called", "tool_finished"]


def test_tool_executor_rejects_invalid_output_schema(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            output_required_keys=["documents"],
            handler=lambda payload: {"items": []},
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))

    result = executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_schema",
            tool_name="PolicyRAGTool",
            called_by="PolicyRAGAgent",
            input={"query": "工伤认定"},
        ),
    )

    assert result.tool_status == "failed"
    assert result.tool_error_code == "tool_output_schema_invalid"
    assert result.fallback_reason == "tool_output_schema_invalid"


def test_tool_executor_rejects_duplicate_tool_call(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            output_required_keys=["documents"],
            handler=lambda payload: {"documents": []},
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))
    request = ToolCallRequest(
        tool_call_id="tool_duplicate",
        tool_name="PolicyRAGTool",
        called_by="PolicyRAGAgent",
        input={"query": "工伤认定"},
    )

    first = executor.execute("req_1", "sess_1", request)
    second = executor.execute("req_1", "sess_1", request)

    assert first.tool_status == "success"
    assert second.tool_status == "failed"
    assert second.tool_error_code == "duplicate_tool_call"


def test_tool_executor_times_out_slow_handler(tmp_path):
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
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))

    result = executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_timeout",
            tool_name="PolicyRAGTool",
            called_by="PolicyRAGAgent",
            input={"query": "工伤认定"},
        ),
    )

    assert result.tool_status == "failed"
    assert result.tool_error_code == "tool_timeout"
    assert result.fallback_reason == "tool_timeout"
