"""AgentDefinition 的只读装配合同测试。"""

from collections.abc import AsyncIterator
from dataclasses import FrozenInstanceError

import pytest

from agent_kernel.agent import AgentDefinition
from agent_kernel.model import (
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
)


class StubModel:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("C1 must not call the model")

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        async def empty() -> AsyncIterator[ModelStreamChunk]:
            if False:
                yield ModelStreamChunk(text_delta="unreachable")

        return empty()


class InvalidModel:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError


def test_agent_definition_is_frozen_and_uses_identity_equality() -> None:
    model = StubModel()
    definition = AgentDefinition(
        definition_id="calculator",
        revision="1",
        instructions="Return a structured calculation result.",
        model=model,
        max_model_rounds=2,
    )
    same_fields = AgentDefinition(
        definition_id="calculator",
        revision="1",
        instructions="Return a structured calculation result.",
        model=model,
        max_model_rounds=2,
    )

    assert definition.model is model
    assert definition != same_fields

    with pytest.raises(FrozenInstanceError):
        definition.instructions = "changed"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("definition_id", ""),
        ("definition_id", "   "),
        ("revision", ""),
        ("instructions", "   "),
    ],
)
def test_agent_definition_rejects_blank_text_fields(
    field_name: str,
    value: str,
) -> None:
    values = {
        "definition_id": "calculator",
        "revision": "1",
        "instructions": "Calculate.",
    }
    values[field_name] = value

    with pytest.raises(ValueError):
        AgentDefinition(
            **values,
            model=StubModel(),
            max_model_rounds=1,
        )


@pytest.mark.parametrize("max_model_rounds", [0, -1, True, 1.5])
def test_agent_definition_rejects_invalid_model_round_limits(
    max_model_rounds: object,
) -> None:
    with pytest.raises(ValueError):
        AgentDefinition(
            definition_id="calculator",
            revision="1",
            instructions="Calculate.",
            model=StubModel(),
            max_model_rounds=max_model_rounds,
        )


def test_agent_definition_rejects_objects_outside_model_protocol() -> None:
    with pytest.raises(ValueError, match="Model Protocol"):
        AgentDefinition(
            definition_id="calculator",
            revision="1",
            instructions="Calculate.",
            model=InvalidModel(),
            max_model_rounds=1,
        )
