"""B2 Model Protocol 的共享合同测试。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from agent_kernel.contracts import KernelError
from agent_kernel.model import (
    FinishReason,
    Model,
    ModelError,
    ModelErrorCode,
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
    Usage,
)


class SuccessfulModel:
    """用于合同测试的最小真实行为替身，不属于生产实现。"""

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            text=request.input if isinstance(request.input, str) else "structured",
            usage=Usage(input_tokens=1, output_tokens=1, total_tokens=2),
            finish_reason=FinishReason.STOP,
            model_id="contract-model",
        )

    async def _stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        yield ModelStreamChunk(text_delta="part-1")
        yield ModelStreamChunk(text_delta="part-2")
        yield ModelStreamChunk(
            finish_reason=FinishReason.STOP,
            usage=Usage(input_tokens=1, output_tokens=2, total_tokens=3),
            model_id="contract-model",
        )

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        return self._stream(request)


class FailingModel:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise ModelError(
            ModelErrorCode.TIMEOUT,
            "model request timed out",
            retryable=True,
        )

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        async def fail() -> AsyncIterator[ModelStreamChunk]:
            raise ModelError(ModelErrorCode.CANCELLED, "stream cancelled")
            yield ModelStreamChunk(text_delta="unreachable")

        return fail()


def test_model_protocol_is_runtime_checkable_and_generate_contract_is_stable() -> None:
    model = SuccessfulModel()
    request = ModelRequest(input="hello")

    assert isinstance(model, Model)
    response = asyncio.run(model.generate(request))

    assert response.text == "hello"
    assert response.finish_reason is FinishReason.STOP


def test_model_stream_contract_is_async_and_emits_ordered_chunks() -> None:
    model = SuccessfulModel()
    request = ModelRequest(input="hello")

    async def consume() -> list[ModelStreamChunk]:
        return [chunk async for chunk in model.stream(request)]

    chunks = asyncio.run(consume())

    assert [chunk.text_delta for chunk in chunks[:2]] == ["part-1", "part-2"]
    assert chunks[-1].finish_reason is FinishReason.STOP
    assert chunks[-1].usage is not None


def test_model_errors_are_provider_neutral_and_preserve_retryability() -> None:
    error = ModelError(
        ModelErrorCode.RATE_LIMIT,
        "provider rate limit",
        retryable=True,
        details={"retry_after_seconds": 2},
    )

    assert error.code is ModelErrorCode.RATE_LIMIT
    assert isinstance(error, KernelError)
    assert error.retryable is True
    assert error.details == {"retry_after_seconds": 2}
    assert str(error) == "provider rate limit"


def test_model_contract_failure_paths_use_model_error() -> None:
    model = FailingModel()
    request = ModelRequest(input="hello")

    with pytest.raises(ModelError) as error_info:
        asyncio.run(model.generate(request))

    assert error_info.value.code is ModelErrorCode.TIMEOUT

    async def consume() -> None:
        async for _ in model.stream(request):
            pass

    with pytest.raises(ModelError) as error_info:
        asyncio.run(consume())

    assert error_info.value.code is ModelErrorCode.CANCELLED
