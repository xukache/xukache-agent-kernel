"""B1 ModelRequest / ModelResponse 契约测试。"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from agent_kernel.model import (
    FinishReason,
    MessageRole,
    ModelMessage,
    ModelMemoryItem,
    ModelRequest,
    ModelResponse,
    ToolCall,
    ToolSchema,
    Usage,
)


def test_model_request_is_strict_immutable_and_json_serializable() -> None:
    request = ModelRequest(
        instructions="你是一个只返回结构化结果的助手。",
        input="请计算 18 + 24。",
        context=(ModelMessage(role=MessageRole.USER, content="开始"),),
        memory_items=(
            ModelMemoryItem(
                memory_id="memory-1",
                content="用户正在学习 Agent Kernel。",
                source="test",
            ),
        ),
        tool_schemas=(
            ToolSchema(
                name="add",
                description="计算两个整数的和",
                input_schema={
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                },
            ),
        ),
        output_schema={
            "type": "object",
            "properties": {"result": {"type": "integer"}},
            "required": ["result"],
        },
        runtime_metadata={"trace_id": "trace-1"},
    )

    assert request.model_copy(update={"input": "新问题"}).input == "新问题"
    assert json.loads(request.model_dump_json())["tool_schemas"][0]["name"] == "add"

    with pytest.raises(ValidationError):
        request.input = "不能原地修改"

    with pytest.raises(ValidationError):
        ModelRequest(instructions="x", input=42)


def test_model_response_supports_structured_output_and_usage() -> None:
    response = ModelResponse(
        structured_output={"result": 42},
        usage=Usage(input_tokens=8, output_tokens=3, total_tokens=11),
        finish_reason=FinishReason.STOP,
        model_id="provider-model",
        provider_metadata={"request_id": "request-1"},
    )

    assert response.structured_output == {"result": 42}
    assert response.usage.total_tokens == 11
    assert response.finish_reason is FinishReason.STOP
    assert response.model_dump(mode="json")["provider_metadata"]["request_id"] == (
        "request-1"
    )


def test_model_response_represents_tool_call_without_exposing_callable() -> None:
    response = ModelResponse(
        tool_calls=(
            ToolCall(
                call_id="call-1",
                name="add",
                arguments={"a": 18, "b": 24},
            ),
        ),
        usage=Usage(),
        finish_reason=FinishReason.TOOL_CALL,
        model_id="provider-model",
    )

    assert response.tool_calls[0].name == "add"
    assert response.tool_calls[0].arguments == {"a": 18, "b": 24}
    assert not hasattr(response.tool_calls[0], "execute")


def test_model_response_rejects_inconsistent_finish_reason() -> None:
    with pytest.raises(ValidationError):
        ModelResponse(
            text="最终答案",
            tool_calls=(
                ToolCall(
                    call_id="call-1",
                    name="add",
                    arguments={"a": 1, "b": 2},
                ),
            ),
            usage=Usage(),
            finish_reason=FinishReason.STOP,
            model_id="provider-model",
        )

    with pytest.raises(ValidationError):
        ModelResponse(
            usage=Usage(),
            finish_reason=FinishReason.TOOL_CALL,
            model_id="provider-model",
        )
