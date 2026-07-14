"""ModelRequest 与 ModelResponse 的 Provider Neutral Schema。

本模块只表达数据，不执行模型调用，不持有可执行 Tool，也不依赖 Provider SDK。
"""

from __future__ import annotations

from enum import Enum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import TypeAliasType

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue = TypeAliasType(
    "JsonValue",
    JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"],
)
JsonObject = TypeAliasType("JsonObject", dict[str, JsonValue])


class ModelSchema(BaseModel):
    """Model 数据跨越 Core 与 Adapter 时使用的严格不可变基类。"""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )


class MessageRole(str, Enum):
    """Provider Neutral 的消息角色。"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(str, Enum):
    """Model 一次生成结束的稳定原因。"""

    STOP = "stop"
    TOOL_CALL = "tool_call"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    CANCELLED = "cancelled"


class Usage(ModelSchema):
    """归一化的 Token 使用量；Provider 未提供的值保持 None。"""

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class ModelMessage(ModelSchema):
    """Model 上下文中的一条消息，不携带 Provider SDK 对象。"""

    role: MessageRole
    content: str | JsonObject


class ModelMemoryItem(ModelSchema):
    """Memory 进入 Model 请求时的最小只读投影。"""

    memory_id: str
    content: str
    source: str | None = None


class ToolSchema(ModelSchema):
    """Model 可见的工具描述，不是可执行 Tool。"""

    name: str
    description: str
    input_schema: JsonObject


class ToolCall(ModelSchema):
    """Model 返回的结构化调用意图，不包含 Python callable。"""

    call_id: str
    name: str
    arguments: JsonObject


class ToolCallDelta(ModelSchema):
    """Streaming 中的部分 Tool Call，不要求每个 chunk 都完整。"""

    call_id: str | None = None
    name: str | None = None
    arguments_delta: str | None = None

    @model_validator(mode="after")
    def validate_delta(self) -> ToolCallDelta:
        if self.call_id is None and self.name is None and self.arguments_delta is None:
            raise ValueError("ToolCallDelta requires at least one delta field")
        return self


class ModelStreamChunk(ModelSchema):
    """Model stream 的一个有序增量或终止标记。"""

    text_delta: str | None = None
    structured_delta: JsonObject | None = None
    tool_call_delta: ToolCallDelta | None = None
    usage: Usage | None = None
    finish_reason: FinishReason | None = None
    model_id: str | None = None

    @model_validator(mode="after")
    def validate_chunk(self) -> ModelStreamChunk:
        if (
            self.text_delta is None
            and self.structured_delta is None
            and self.tool_call_delta is None
            and self.usage is None
            and self.finish_reason is None
        ):
            raise ValueError("ModelStreamChunk requires a delta or terminal field")
        return self


class ModelRequest(ModelSchema):
    """Agent 交给 Model Adapter 的一次 Provider Neutral 请求。"""

    instructions: str | None = None
    input: str | JsonObject
    context: tuple[ModelMessage, ...] = ()
    memory_items: tuple[ModelMemoryItem, ...] = ()
    tool_schemas: tuple[ToolSchema, ...] = ()
    output_schema: JsonObject | None = None
    runtime_metadata: JsonObject = {}


class ModelResponse(ModelSchema):
    """Model Adapter 返回给 Agent 的一次归一化响应。"""

    text: str | None = None
    structured_output: JsonObject | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage
    finish_reason: FinishReason
    model_id: str
    provider_metadata: JsonObject = {}

    @model_validator(mode="after")
    def validate_output_and_finish_reason(self) -> ModelResponse:
        """保证响应至少有一种输出，并约束 Tool Call 与结束原因一致。"""
        if self.text is None and self.structured_output is None and not self.tool_calls:
            raise ValueError(
                "ModelResponse requires text, structured_output, or tool_calls"
            )
        if self.finish_reason is FinishReason.TOOL_CALL and not self.tool_calls:
            raise ValueError("tool_call finish_reason requires at least one tool call")
        if self.finish_reason is FinishReason.STOP and self.tool_calls:
            raise ValueError("stop finish_reason cannot contain tool calls")
        return self
