from __future__ import annotations

from ananhu_agent.capabilities.contracts import (
    CapabilityError,
    CapabilityGateway,
    CapabilityIdempotency,
    CapabilityPolicy,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
)
from ananhu_agent.schemas import ToolCallRequest
from ananhu_agent.tools.executor import ToolExecutor


class ToolExecutorCapabilityGateway(CapabilityGateway):
    """基于现有 ToolExecutor 的能力网关适配器。

    该适配器只做协议转换、调用身份补充和 logical_call_id 去重，不绕过 ToolExecutor
    既有的权限、schema、超时、错误归一和 trace 行为。
    """

    def __init__(self, tool_executor: ToolExecutor) -> None:
        self.tool_executor = tool_executor
        # 任务 28 的最小幂等存储：同一进程内相同 logical_call_id 只执行一次底层工具。
        # 后续接入持久化幂等记录时，需要把 run_id、capability_version 纳入键。
        self._results_by_logical_call_id: dict[str, CapabilityResult] = {}

    @property
    def trace_recorder(self):
        """暴露底层 trace recorder，便于组合根和测试读取运行证据。"""

        return self.tool_executor.trace_recorder

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        """执行能力请求，并对重复 logical_call_id 做幂等复用。

        参数:
            request: Runtime/阶段服务发起的能力请求。

        返回:
            `CapabilityResult`。首次调用会经过 ToolExecutor；重复逻辑调用返回缓存结果，
            但保留本次请求的 `attempt`，用于区分物理重试。
        """

        if request.logical_call_id in self._results_by_logical_call_id:
            cached = self._results_by_logical_call_id[request.logical_call_id]
            return cached.model_copy(update={"attempt": request.attempt, "reused": True}, deep=True)

        definition = self.tool_executor.registry.get(request.capability_name)
        policy = _policy_from_definition(request.capability_name, definition)
        # ToolExecutor 仍是当前唯一实际执行入口；网关只把能力协议转换成旧工具协议。
        tool_request = ToolCallRequest(
            tool_call_id=request.logical_call_id,
            tool_name=request.capability_name,
            called_by=request.caller,
            input=request.input,
        )
        tool_result = self.tool_executor.execute(
            request.request_id,
            request.session_id,
            tool_request,
            runtime_name="native",
            runtime_version=request.schema_version,
            node_id=request.node_id,
            logical_call_id=request.logical_call_id,
            attempt=request.attempt,
        )
        status = (
            CapabilityStatus.SUCCESS
            if tool_result.tool_status == "success"
            else CapabilityStatus.FAILED
        )
        # 失败码沿用 ToolExecutor 的稳定错误码，保证旧治理语义不被适配层改写。
        result = CapabilityResult(
            request_id=request.request_id,
            session_id=request.session_id,
            capability_name=request.capability_name,
            caller=request.caller,
            node_id=request.node_id,
            logical_call_id=request.logical_call_id,
            attempt=request.attempt,
            status=status,
            policy=policy,
            output=tool_result.output,
            error=(
                CapabilityError(
                    code=tool_result.tool_error_code or "capability_failed",
                    message=tool_result.fallback_reason or tool_result.tool_error_code or "capability failed",
                )
                if status is CapabilityStatus.FAILED
                else None
            ),
            tool_call_result=tool_result.model_dump(),
        )
        self._results_by_logical_call_id[request.logical_call_id] = result
        return result


def _policy_from_definition(capability_name: str, definition) -> CapabilityPolicy:
    """从 ToolDefinition 推导能力治理策略。

    参数:
        capability_name: 能力名称，当前与 ToolDefinition.name 一致。
        definition: ToolRegistry 中的工具定义；未知能力时可能为空。

    返回:
        能力策略快照。未知能力按 side_effecting 处理，避免误判为可安全重放。
    """

    if definition is None:
        return CapabilityPolicy(
            risk_level="unknown",
            timeout_ms=0,
            idempotency=CapabilityIdempotency.SIDE_EFFECTING,
        )
    return CapabilityPolicy(
        risk_level=definition.risk_level,
        timeout_ms=definition.timeout_ms,
        idempotency=_idempotency_for(capability_name, definition.risk_level),
    )


def _idempotency_for(capability_name: str, risk_level: str) -> CapabilityIdempotency:
    """按现有工具风险和能力名称声明 MVP 幂等等级。

    read_only 工具可重复读取；待遇测算是确定性计算；其他能力先按有副作用处理。
    """

    if risk_level == "read_only":
        return CapabilityIdempotency.READ_ONLY_REPEATABLE
    if capability_name == "PaymentCalculationTool" or risk_level == "calculation":
        return CapabilityIdempotency.DETERMINISTIC
    return CapabilityIdempotency.SIDE_EFFECTING
