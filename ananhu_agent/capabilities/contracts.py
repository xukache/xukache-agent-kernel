from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# 能力协议版本；后续真实模型、知识库和写操作接入时用它做兼容判断。
CAPABILITY_SCHEMA_VERSION = "capability.v1"


class CapabilityIdempotency(str, Enum):
    """能力幂等等级，决定重复 logical_call_id 的处理策略。"""

    READ_ONLY_REPEATABLE = "read_only_repeatable"
    DETERMINISTIC = "deterministic"
    SIDE_EFFECTING = "side_effecting"


class CapabilityStatus(str, Enum):
    """能力调用的框架中立状态。"""

    SUCCESS = "success"
    FAILED = "failed"


class CapabilityPolicy(BaseModel):
    """能力治理策略快照。"""

    risk_level: str = Field(description="底层工具风险等级。")
    timeout_ms: int = Field(description="单次物理执行超时时间。")
    idempotency: CapabilityIdempotency = Field(description="重复逻辑调用处理策略。")


class CapabilityError(BaseModel):
    """能力失败的结构化错误。"""

    code: str = Field(description="稳定错误码，由能力执行网关统一定义。")
    message: str = Field(description="人类可读错误说明。")


class CapabilityRequest(BaseModel):
    """Runtime 或阶段服务发起的能力调用请求。

    该对象是 Runtime/阶段服务看到的唯一能力执行协议；底层 handler、
    LangGraph ToolNode 或第三方 SDK 类型不得暴露给调用方。
    """

    schema_version: Literal["capability.v1"] = Field(default=CAPABILITY_SCHEMA_VERSION)
    run_id: str = Field(description="单次运行 ID，用于事件、trace 和幂等隔离。")
    request_id: str = Field(description="用户请求 ID，用于 trace 关联。")
    session_id: str = Field(description="会话 ID，用于 trace 关联。")
    capability_name: str = Field(description="显式注册的能力名称。")
    caller: str = Field(description="调用方身份，用于能力权限校验。")
    input: dict[str, Any] = Field(default_factory=dict, description="能力输入。")
    node_id: str = Field(description="发起调用的业务节点或阶段服务。")
    logical_call_id: str = Field(description="逻辑调用 ID，重试时保持不变。")
    attempt: int = Field(default=1, ge=1, description="物理尝试次数，从 1 开始。")
    runtime_name: str = Field(default="native", description="发起调用的项目运行时名称，用于 trace 归属。")
    runtime_version: str = Field(default="workflow.v1", description="发起调用的运行时版本。")


class CapabilityResult(BaseModel):
    """能力网关返回的框架中立结果。

    关键计算字段必须放在 `output`，失败原因必须放在 `error`，不能只写进自然语言。
    """

    schema_version: Literal["capability.v1"] = Field(
        default=CAPABILITY_SCHEMA_VERSION,
        description="能力结果协议版本。",
    )
    request_id: str = Field(description="用户请求 ID，与 CapabilityRequest 保持一致。")
    session_id: str = Field(description="会话 ID，与 CapabilityRequest 保持一致。")
    capability_name: str = Field(description="能力名称，与 CapabilityRequest.capability_name 保持一致。")
    caller: str = Field(description="调用方身份，用于权限审计。")
    node_id: str = Field(description="产生该结果的业务节点或阶段服务。")
    logical_call_id: str = Field(description="逻辑调用 ID；重试复用时保持不变。")
    attempt: int = Field(description="本次返回对应的物理尝试次数。")
    status: CapabilityStatus = Field(description="能力执行状态。")
    policy: CapabilityPolicy = Field(description="本次能力执行使用的治理策略快照。")
    output: dict[str, Any] = Field(default_factory=dict, description="能力结构化输出。")
    error: CapabilityError | None = Field(default=None, description="失败时的结构化错误。")
    reused: bool = Field(default=False, description="是否复用了同一 logical_call_id 的历史结果。")


class CapabilityGateway(ABC):
    """能力执行端口，Runtime/Agent 只能依赖该抽象。"""

    @abstractmethod
    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        """执行一次能力调用。

        参数:
            request: 框架中立能力请求，包含调用身份、逻辑调用 ID 和物理尝试次数。

        返回:
            框架中立能力结果；失败以 `CapabilityResult.error` 表达，不泄漏底层异常类型。
        """
