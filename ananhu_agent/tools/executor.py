from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor as FuturesThreadPoolExecutor
from concurrent.futures import TimeoutError
from time import perf_counter

from ananhu_agent.schemas import ToolCallRequest, ToolCallResult, TraceEvent
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.tools.registry import ToolDefinition, ToolRegistry


class ToolExecutor:
    """统一执行工具调用并写入 trace。

    该层集中处理权限、输入校验和错误归一，避免 Agent 绕过治理直接调用工具函数。
    """

    def __init__(self, registry: ToolRegistry, trace_recorder: TraceRecorder) -> None:
        self.registry = registry
        self.trace_recorder = trace_recorder
        self._call_fingerprints: set[str] = set()

    def execute(
        self,
        request_id: str,
        session_id: str,
        request: ToolCallRequest,
    ) -> ToolCallResult:
        started = perf_counter()
        self._record_called(request_id, session_id, request)
        definition = self.registry.get(request.tool_name)
        if definition is None:
            return self._fail(request_id, session_id, request, "tool_not_registered", started)
        if request.called_by not in definition.allowed_callers:
            return self._fail(request_id, session_id, request, "caller_not_allowed", started)

        fingerprint = self._fingerprint(request_id, request)
        if fingerprint in self._call_fingerprints:
            return self._fail(request_id, session_id, request, "duplicate_tool_call", started)
        self._call_fingerprints.add(fingerprint)

        missing = [key for key in definition.required_input_keys if key not in request.input]
        if missing:
            return self._fail(request_id, session_id, request, "invalid_input_schema", started)

        try:
            output = self._run_with_timeout(definition, request.input)
        except TimeoutError:
            return self._fail(request_id, session_id, request, "tool_timeout", started)
        except Exception:
            return self._fail(request_id, session_id, request, "tool_handler_error", started)

        missing_output = [key for key in definition.output_required_keys if key not in output]
        if missing_output:
            return self._fail(request_id, session_id, request, "tool_output_schema_invalid", started)

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
            fallback_reason=None,
        )
        self._record(request_id, session_id, "tool_finished", result)
        return result

    @staticmethod
    def _run_with_timeout(
        definition: ToolDefinition,
        payload: dict,
    ) -> dict:
        executor = FuturesThreadPoolExecutor(max_workers=1)
        future = executor.submit(definition.handler, payload)
        try:
            return future.result(timeout=definition.timeout_ms / 1000)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

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
            fallback_reason=code,
        )
        self._record(request_id, session_id, "tool_failed", result)
        return result

    def _record_called(
        self,
        request_id: str,
        session_id: str,
        request: ToolCallRequest,
    ) -> None:
        self.trace_recorder.record(
            TraceEvent.new(
                request_id=request_id,
                session_id=session_id,
                event_type="tool_called",
                phase="tool",
                payload=request.model_dump(),
            )
        )

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

    @staticmethod
    def _fingerprint(request_id: str, request: ToolCallRequest) -> str:
        return json.dumps(
            {
                "request_id": request_id,
                "tool_name": request.tool_name,
                "called_by": request.called_by,
                "input": request.input,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
