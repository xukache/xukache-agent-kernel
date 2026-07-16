"""C3 最小 Agent 推理循环的确定性合同测试。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable

import pytest

from agent_kernel.agent import (
    AgentDefinition,
    AgentInput,
    AgentStatus,
    AgentStopReason,
    run_agent,
)
from agent_kernel.contracts import ErrorSource
from agent_kernel.model import (
    FinishReason,
    ModelError,
    ModelErrorCode,
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
    ToolCall,
    Usage,
)


class StubModel:
    """通过可注入行为验证 Agent 与 Model 的单次调用边界。"""

    def __init__(self, behavior: Callable[[ModelRequest], ModelResponse]) -> None:
        self.behavior = behavior
        self.requests: list[ModelRequest] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return self.behavior(request)

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        async def empty() -> AsyncIterator[ModelStreamChunk]:
            if False:
                yield ModelStreamChunk(text_delta="unreachable")

        return empty()


def _definition(model: StubModel) -> AgentDefinition:
    return AgentDefinition(
        definition_id="calculator",
        revision="1",
        instructions="Return a structured calculation result.",
        model=model,
        max_model_rounds=2,
    )


def _response(
    *,
    text: str | None = None,
    structured_output: dict[str, object] | None = None,
    finish_reason: FinishReason = FinishReason.STOP,
    tool_calls: tuple[ToolCall, ...] = (),
    model_id: str = "test-model",
) -> ModelResponse:
    return ModelResponse(
        text=text,
        structured_output=structured_output,
        tool_calls=tool_calls,
        usage=Usage(input_tokens=3, output_tokens=2, total_tokens=5),
        finish_reason=finish_reason,
        model_id=model_id,
    )


def test_run_agent_maps_text_response_to_succeeded_result() -> None:
    model = StubModel(lambda request: _response(text="42"))

    result = asyncio.run(
        run_agent(
            _definition(model),
            AgentInput(input="Calculate 18 + 24."),
        )
    )

    assert result.status is AgentStatus.SUCCEEDED
    assert result.stop_reason is AgentStopReason.COMPLETED
    assert result.output == "42"
    assert result.model_id == "test-model"
    assert result.usage.total_tokens == 5
    assert len(model.requests) == 1
    assert model.requests[0].input == "Calculate 18 + 24."


def test_run_agent_prefers_structured_output() -> None:
    model = StubModel(
        lambda request: _response(
            text='{"result": 42}',
            structured_output={"result": 42},
        )
    )

    result = asyncio.run(
        run_agent(
            _definition(model),
            AgentInput(input="Calculate.", output_schema={"type": "object"}),
        )
    )

    assert result.status is AgentStatus.SUCCEEDED
    assert result.output == {"result": 42}


def test_run_agent_maps_model_error_and_preserves_error_evidence() -> None:
    def fail(request: ModelRequest) -> ModelResponse:
        raise ModelError(
            ModelErrorCode.TIMEOUT,
            "model request timed out",
            retryable=True,
            details={"attempt": 1},
        )

    result = asyncio.run(
        run_agent(_definition(StubModel(fail)), AgentInput(input="Calculate."))
    )

    assert result.status is AgentStatus.FAILED
    assert result.stop_reason is AgentStopReason.ERROR
    assert result.output is None
    assert result.usage == Usage()
    assert result.error is not None
    assert result.error.code == "model.timeout"
    assert result.error.source is ErrorSource.MODEL
    assert result.error.retryable is True
    assert result.error.details == {"attempt": 1}


def test_run_agent_maps_model_cancellation_to_cancelled_result() -> None:
    def cancel(request: ModelRequest) -> ModelResponse:
        raise ModelError(ModelErrorCode.CANCELLED, "model invocation cancelled")

    result = asyncio.run(
        run_agent(_definition(StubModel(cancel)), AgentInput(input="Calculate."))
    )

    assert result.status is AgentStatus.CANCELLED
    assert result.stop_reason is AgentStopReason.CANCELLED
    assert result.error is not None
    assert result.error.code == "model.cancelled"
    assert result.error.source is ErrorSource.MODEL


def test_run_agent_maps_task_cancellation_to_cancelled_result() -> None:
    def cancel(request: ModelRequest) -> ModelResponse:
        raise asyncio.CancelledError

    result = asyncio.run(
        run_agent(_definition(StubModel(cancel)), AgentInput(input="Calculate."))
    )

    assert result.status is AgentStatus.CANCELLED
    assert result.stop_reason is AgentStopReason.CANCELLED
    assert result.error is not None
    assert result.error.code == "agent.cancelled"
    assert result.error.source is ErrorSource.AGENT


def test_run_agent_maps_unexpected_exception_to_internal_failure() -> None:
    def fail(request: ModelRequest) -> ModelResponse:
        raise RuntimeError("provider internals must not leak")

    result = asyncio.run(
        run_agent(_definition(StubModel(fail)), AgentInput(input="Calculate."))
    )

    assert result.status is AgentStatus.FAILED
    assert result.stop_reason is AgentStopReason.ERROR
    assert result.error is not None
    assert result.error.code == "agent.internal"
    assert result.error.source is ErrorSource.AGENT
    assert result.error.message == "Agent execution failed"
    assert "provider internals" not in result.error.message


def test_run_agent_rejects_unhandled_tool_call_in_c3() -> None:
    tool_call = ToolCall(
        call_id="call-1",
        name="add",
        arguments={"a": 9, "b": 6},
    )
    model = StubModel(
        lambda request: _response(
            finish_reason=FinishReason.TOOL_CALL,
            tool_calls=(tool_call,),
        )
    )

    result = asyncio.run(
        run_agent(_definition(model), AgentInput(input="Calculate."))
    )

    assert result.status is AgentStatus.FAILED
    assert result.stop_reason is AgentStopReason.ERROR
    assert result.tool_calls == (tool_call,)
    assert result.error is not None
    assert result.error.code == "agent.internal"


def test_run_agent_stops_at_max_model_rounds_before_unhandled_tool_call() -> None:
    tool_call = ToolCall(
        call_id="call-1",
        name="add",
        arguments={"a": 9, "b": 6},
    )
    model = StubModel(
        lambda request: _response(
            finish_reason=FinishReason.TOOL_CALL,
            tool_calls=(tool_call,),
        )
    )
    definition = AgentDefinition(
        definition_id="calculator",
        revision="1",
        instructions="Return a structured calculation result.",
        model=model,
        max_model_rounds=1,
    )

    result = asyncio.run(
        run_agent(definition, AgentInput(input="Calculate."))
    )

    assert result.status is AgentStatus.FAILED
    assert result.stop_reason is AgentStopReason.MAX_MODEL_ROUNDS
    assert result.tool_calls == (tool_call,)
    assert result.model_id == "test-model"
    assert result.usage.total_tokens == 5
    assert result.error is not None
    assert result.error.code == "agent.limit"
    assert result.error.source is ErrorSource.AGENT
    assert result.error.retryable is False
    assert result.error.details == {
        "max_model_rounds": 1,
        "rounds": 1,
    }
