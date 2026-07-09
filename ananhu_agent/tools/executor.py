from __future__ import annotations

from time import perf_counter

from ananhu_agent.schemas import ToolCallRequest, ToolCallResult, TraceEvent
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.tools.registry import ToolRegistry


class ToolExecutor:
    """统一执行工具调用并写入 trace。

    该层集中处理权限、输入校验和错误归一，避免 Agent 绕过治理直接调用工具函数。
    """

    def __init__(self, registry: ToolRegistry, trace_recorder: TraceRecorder) -> None:
        self.registry = registry
        self.trace_recorder = trace_recorder

    def execute(
        self,
        request_id: str,
        session_id: str,
        request: ToolCallRequest,
    ) -> ToolCallResult:
        started = perf_counter()
        definition = self.registry.get(request.tool_name)
        if definition is None:
            return self._fail(request_id, session_id, request, "tool_not_registered", started)
        if request.called_by not in definition.allowed_callers:
            return self._fail(request_id, session_id, request, "caller_not_allowed", started)

        missing = [key for key in definition.required_input_keys if key not in request.input]
        if missing:
            return self._fail(request_id, session_id, request, "invalid_input_schema", started)

        try:
            output = definition.handler(request.input)
        except Exception:
            return self._fail(request_id, session_id, request, "tool_handler_error", started)

        result = ToolCallResult(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            called_by=request.called_by,
            tool_status="success",
            tool_error_code=None,
            latency_ms=int((perf_counter() - started) * 1000),
            input=request.input,
            output=output,
            fallback_used=False,
        )
        self._record(request_id, session_id, "tool_finished", result)
        return result

    def _fail(
        self,
        request_id: str,
        session_id: str,
        request: ToolCallRequest,
        code: str,
        started: float,
    ) -> ToolCallResult:
        result = ToolCallResult(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            called_by=request.called_by,
            tool_status="failed",
            tool_error_code=code,
            latency_ms=int((perf_counter() - started) * 1000),
            input=request.input,
            output={},
            fallback_used=True,
        )
        self._record(request_id, session_id, "tool_failed", result)
        return result

    def _record(
        self,
        request_id: str,
        session_id: str,
        event_type: str,
        result: ToolCallResult,
    ) -> None:
        self.trace_recorder.record(
            TraceEvent.new(
                request_id=request_id,
                session_id=session_id,
                event_type=event_type,
                phase="tool",
                payload=result.model_dump(),
                latency_ms=result.latency_ms,
            )
        )
