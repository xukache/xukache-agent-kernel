"""C2 ModelRequest Builder 的确定性合同测试。"""

from collections.abc import AsyncIterator

from agent_kernel.agent import (
    AgentDefinition,
    AgentInput,
    build_model_request,
)
from agent_kernel.model import ModelRequest, ModelResponse, ModelStreamChunk


class StubModel:
    """只用于证明 Builder 不会触发 Model 调用。"""

    def __init__(self) -> None:
        self.generate_called = False
        self.stream_called = False

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_called = True
        raise AssertionError("C2 Builder must not call generate")

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        self.stream_called = True

        async def empty() -> AsyncIterator[ModelStreamChunk]:
            if False:
                yield ModelStreamChunk(text_delta="unreachable")

        return empty()


def test_build_model_request_maps_owned_fields_and_keeps_defaults() -> None:
    model = StubModel()
    definition = AgentDefinition(
        definition_id="calculator",
        revision="1",
        instructions="Return only the requested JSON result.",
        model=model,
        max_model_rounds=2,
    )
    agent_input = AgentInput(
        input="Calculate 9 + 6.",
        output_schema={
            "type": "object",
            "properties": {"result": {"type": "integer"}},
            "required": ["result"],
        },
        application_metadata={"request_id": "ignored-by-c2"},
    )

    request = build_model_request(definition, agent_input)

    assert request.instructions == definition.instructions
    assert request.input == agent_input.input
    assert request.output_schema == agent_input.output_schema
    assert request.context == ()
    assert request.memory_items == ()
    assert request.tool_schemas == ()
    assert request.runtime_metadata == {}
    assert "request_id" not in request.runtime_metadata
    assert not model.generate_called
    assert not model.stream_called


def test_build_model_request_returns_a_model_request_schema() -> None:
    definition = AgentDefinition(
        definition_id="echo",
        revision="1",
        instructions="Echo the input.",
        model=StubModel(),
        max_model_rounds=1,
    )
    agent_input = AgentInput(
        input={"message": "hello"},
        application_metadata={"trace_id": "caller-owned"},
    )

    request = build_model_request(definition, agent_input)

    assert isinstance(request, ModelRequest)
    assert request.input == {"message": "hello"}
    assert request.output_schema is None
