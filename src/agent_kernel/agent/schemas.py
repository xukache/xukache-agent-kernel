"""Agent 单次调用输入和最终结果 Schema。"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator, model_validator

from agent_kernel.contracts import ErrorInfo, JsonObject, KernelSchema
from agent_kernel.model import ToolCall, Usage


class AgentInput(KernelSchema):
    """本次 Agent 调用数据，不重复携带 Definition 装配。"""

    input: str | JsonObject
    output_schema: JsonObject | None = None
    application_metadata: JsonObject = Field(default_factory=dict)

    @field_validator("input")
    @classmethod
    def reject_blank_text_input(
        cls,
        value: str | JsonObject,
    ) -> str | JsonObject:
        if isinstance(value, str) and not value.strip():
            raise ValueError("agent input text must not be blank")
        return value


class AgentStatus(str, Enum):
    """Agent 一次调用支持的终态。"""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStopReason(str, Enum):
    """Agent 推理循环停止的高层原因。"""

    COMPLETED = "completed"
    MAX_MODEL_ROUNDS = "max_model_rounds"
    ERROR = "error"
    CANCELLED = "cancelled"


class AgentResult(KernelSchema):
    """一次 Agent 调用的最终结构化结果，不承担 Runtime Result 职责。"""

    status: AgentStatus
    output: str | JsonObject | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage
    model_id: str | None = None
    stop_reason: AgentStopReason
    error: ErrorInfo | None = None

    @field_validator("model_id")
    @classmethod
    def reject_blank_model_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("model_id must not be blank")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self) -> AgentResult:
        if self.status is AgentStatus.SUCCEEDED:
            if self.output is None:
                raise ValueError("succeeded result requires output")
            if self.model_id is None:
                raise ValueError("succeeded result requires model_id")
            if self.error is not None:
                raise ValueError("succeeded result cannot include error")
            if self.stop_reason is not AgentStopReason.COMPLETED:
                raise ValueError("succeeded result must stop as completed")
            return self

        if self.status is AgentStatus.FAILED:
            if self.output is not None:
                raise ValueError("failed result cannot include output")
            if self.error is None:
                raise ValueError("failed result requires error")
            if self.stop_reason not in {
                AgentStopReason.ERROR,
                AgentStopReason.MAX_MODEL_ROUNDS,
            }:
                raise ValueError("failed result has invalid stop_reason")
            return self

        if self.output is not None:
            raise ValueError("cancelled result cannot include output")
        if self.error is None:
            raise ValueError("cancelled result requires error")
        if self.stop_reason is not AgentStopReason.CANCELLED:
            raise ValueError("cancelled result must stop as cancelled")
        return self
