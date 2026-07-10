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
        runtime_name: str | None = None,
        runtime_version: str | None = None,
        node_id: str | None = None,
        logical_call_id: str | None = None,
        attempt: int | None = None,
        run_id: str | None = None,
    ) -> ToolCallResult:
        """执行一次工具调用。

        参数:
            request_id: 用户请求 ID。
            session_id: 会话 ID。
            request: Agent 或 CapabilityGateway 发出的工具调用请求。
            runtime_name: 发起调用的运行时名称；旧调用可为空。
            runtime_version: 运行时或能力协议版本；旧调用可为空。
            node_id: 发起调用的业务节点；用于 trace 关联。
            logical_call_id: 稳定逻辑调用 ID；重试时不变。
            attempt: 物理尝试次数；重试时递增。
            run_id: 单次运行 ID；CapabilityGateway 新调用必须提供。

        返回:
            归一化 `ToolCallResult`，成功和失败都会写入项目 trace。
        """

        started = perf_counter()
        self._record_called(
            request_id,
            session_id,
            request,
            runtime_name=runtime_name,
            runtime_version=runtime_version,
            node_id=node_id,
            logical_call_id=logical_call_id,
            attempt=attempt,
            run_id=run_id,
        )
        definition = self.registry.get(request.tool_name)
        if definition is None:
            return self._fail(
                request_id,
                session_id,
                request,
                "tool_not_registered",
                started,
                runtime_name,
                runtime_version,
                node_id,
                logical_call_id,
                attempt,
                run_id,
            )
        if request.called_by not in definition.allowed_callers:
            return self._fail(
                request_id,
                session_id,
                request,
                "caller_not_allowed",
                started,
                runtime_name,
                runtime_version,
                node_id,
                logical_call_id,
                attempt,
                run_id,
            )

        fingerprint = self._fingerprint(request_id, request)
        if fingerprint in self._call_fingerprints:
            return self._fail(
                request_id,
                session_id,
                request,
                "duplicate_tool_call",
                started,
                runtime_name,
                runtime_version,
                node_id,
                logical_call_id,
                attempt,
                run_id,
            )
        self._call_fingerprints.add(fingerprint)

        missing = [key for key in definition.required_input_keys if key not in request.input]
        if missing:
            return self._fail(
                request_id,
                session_id,
                request,
                "invalid_input_schema",
                started,
                runtime_name,
                runtime_version,
                node_id,
                logical_call_id,
                attempt,
                run_id,
            )

        try:
            output = self._run_with_timeout(definition, request.input)
        except TimeoutError:
            return self._fail(
                request_id,
                session_id,
                request,
                "tool_timeout",
                started,
                runtime_name,
                runtime_version,
                node_id,
                logical_call_id,
                attempt,
                run_id,
            )
        except Exception:
            return self._fail(
                request_id,
                session_id,
                request,
                "tool_handler_error",
                started,
                runtime_name,
                runtime_version,
                node_id,
                logical_call_id,
                attempt,
                run_id,
            )

        missing_output = [key for key in definition.output_required_keys if key not in output]
        if missing_output:
            return self._fail(
                request_id,
                session_id,
                request,
                "tool_output_schema_invalid",
                started,
                runtime_name,
                runtime_version,
                node_id,
                logical_call_id,
                attempt,
                run_id,
            )

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
        self._record(
            request_id,
            session_id,
            "tool_finished",
            result,
            runtime_name=runtime_name,
            runtime_version=runtime_version,
            node_id=node_id,
            logical_call_id=logical_call_id,
            attempt=attempt,
            run_id=run_id,
        )
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
        runtime_name: str | None = None,
        runtime_version: str | None = None,
        node_id: str | None = None,
        logical_call_id: str | None = None,
        attempt: int | None = None,
        run_id: str | None = None,
    ) -> ToolCallResult:
        """构造失败结果并写入 trace，保留调用身份字段。"""

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
        self._record(
            request_id,
            session_id,
            "tool_failed",
            result,
            runtime_name=runtime_name,
            runtime_version=runtime_version,
            node_id=node_id,
            logical_call_id=logical_call_id,
            attempt=attempt,
            run_id=run_id,
        )
        return result

    def _record_called(
        self,
        request_id: str,
        session_id: str,
        request: ToolCallRequest,
        runtime_name: str | None = None,
        runtime_version: str | None = None,
        node_id: str | None = None,
        logical_call_id: str | None = None,
        attempt: int | None = None,
        run_id: str | None = None,
    ) -> None:
        """记录工具调用开始事件。"""

        self.trace_recorder.record(
            TraceEvent.new(
                request_id=request_id,
                run_id=run_id,
                session_id=session_id,
                event_type="tool_called",
                phase="tool",
                runtime_name=runtime_name,
                runtime_version=runtime_version,
                node_id=node_id,
                logical_call_id=logical_call_id,
                attempt=attempt,
                payload=request.model_dump(),
            )
        )

    def _record(
        self,
        request_id: str,
        session_id: str,
        event_type: str,
        result: ToolCallResult,
        runtime_name: str | None = None,
        runtime_version: str | None = None,
        node_id: str | None = None,
        logical_call_id: str | None = None,
        attempt: int | None = None,
        run_id: str | None = None,
    ) -> None:
        """记录工具调用完成或失败事件。"""

        self.trace_recorder.record(
            TraceEvent.new(
                request_id=request_id,
                run_id=run_id,
                session_id=session_id,
                event_type=event_type,
                phase="tool",
                runtime_name=runtime_name,
                runtime_version=runtime_version,
                node_id=node_id,
                logical_call_id=logical_call_id,
                attempt=attempt,
                payload=result.model_dump(),
                latency_ms=result.latency_ms,
            )
        )

    @staticmethod
    def _fingerprint(request_id: str, request: ToolCallRequest) -> str:
        """生成旧 ToolExecutor 的重复调用指纹。

        该指纹不包含 logical_call_id；任务 28 之后，逻辑重试应优先由
        CapabilityGateway 复用结果，避免重复进入 ToolExecutor。
        """

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
