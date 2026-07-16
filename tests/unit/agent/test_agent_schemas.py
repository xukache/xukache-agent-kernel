"""AgentInput 和 AgentResult 的确定性合同测试。"""

import json

import pytest
from pydantic import ValidationError

from agent_kernel.agent import (
    AgentInput,
    AgentResult,
    AgentStatus,
    AgentStopReason,
)
from agent_kernel.contracts import ErrorInfo, ErrorSource
from agent_kernel.model import ToolCall, Usage


def test_agent_input_is_strict_serializable_and_deeply_immutable() -> None:
    source = {
        "input": {"numbers": [9, 6]},
        "output_schema": {
            "type": "object",
            "required": ["result"],
        },
        "application_metadata": {
            "source": "learning",
            "labels": ["rd-002"],
        },
    }
    agent_input = AgentInput(**source)

    source["input"]["numbers"].append(100)
    source["application_metadata"]["labels"].append("changed")

    assert agent_input.input == {"numbers": [9, 6]}
    assert agent_input.application_metadata == {
        "source": "learning",
        "labels": ["rd-002"],
    }
    assert json.loads(agent_input.model_dump_json())["output_schema"]["required"] == [
        "result"
    ]

    with pytest.raises(TypeError, match="frozen JSON"):
        agent_input.input["numbers"].append(1)  # type: ignore[index,union-attr]


@pytest.mark.parametrize("input_value", ["", "   ", 42])
def test_agent_input_rejects_blank_text_and_invalid_types(
    input_value: object,
) -> None:
    with pytest.raises(ValidationError):
        AgentInput(input=input_value)


def test_agent_input_allows_empty_structured_input_and_rejects_extra_fields() -> None:
    assert AgentInput(input={}).input == {}

    with pytest.raises(ValidationError):
        AgentInput(input="calculate", model="provider-model")


def test_agent_result_supports_success_failure_and_cancellation() -> None:
    succeeded = AgentResult(
        status=AgentStatus.SUCCEEDED,
        output={"result": 15},
        usage=Usage(input_tokens=10, output_tokens=3, total_tokens=13),
        model_id="real-model",
        stop_reason=AgentStopReason.COMPLETED,
    )
    failed = AgentResult(
        status=AgentStatus.FAILED,
        usage=Usage(),
        stop_reason=AgentStopReason.MAX_MODEL_ROUNDS,
        error=ErrorInfo(
            code="agent.limit",
            message="maximum model rounds reached",
            source=ErrorSource.AGENT,
            retryable=False,
        ),
        tool_calls=(
            ToolCall(
                call_id="call-1",
                name="add",
                arguments={"a": 9, "b": 6},
            ),
        ),
    )
    cancelled = AgentResult(
        status=AgentStatus.CANCELLED,
        usage=Usage(),
        stop_reason=AgentStopReason.CANCELLED,
        error=ErrorInfo(
            code="model.cancelled",
            message="model invocation cancelled",
            source=ErrorSource.MODEL,
            retryable=False,
        ),
    )

    assert succeeded.output == {"result": 15}
    assert succeeded.model_id == "real-model"
    assert failed.error is not None
    assert failed.error.code == "agent.limit"
    assert failed.tool_calls[0].name == "add"
    assert cancelled.status is AgentStatus.CANCELLED

    round_trip = AgentResult.model_validate_json(succeeded.model_dump_json())

    assert round_trip == succeeded


@pytest.mark.parametrize(
    "result_data",
    [
        {
            "status": AgentStatus.SUCCEEDED,
            "output": None,
            "usage": Usage(),
            "model_id": "model",
            "stop_reason": AgentStopReason.COMPLETED,
        },
        {
            "status": AgentStatus.SUCCEEDED,
            "output": "done",
            "usage": Usage(),
            "model_id": None,
            "stop_reason": AgentStopReason.COMPLETED,
        },
        {
            "status": AgentStatus.FAILED,
            "output": "partial",
            "usage": Usage(),
            "stop_reason": AgentStopReason.ERROR,
            "error": ErrorInfo(
                code="model.format",
                message="invalid output",
                source=ErrorSource.MODEL,
                retryable=False,
            ),
        },
        {
            "status": AgentStatus.FAILED,
            "usage": Usage(),
            "stop_reason": AgentStopReason.ERROR,
            "error": None,
        },
        {
            "status": AgentStatus.CANCELLED,
            "usage": Usage(),
            "stop_reason": AgentStopReason.ERROR,
            "error": ErrorInfo(
                code="agent.cancelled",
                message="cancelled",
                source=ErrorSource.AGENT,
                retryable=False,
            ),
        },
    ],
)
def test_agent_result_rejects_invalid_status_combinations(
    result_data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AgentResult(**result_data)
