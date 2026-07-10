from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from ananhu_agent.infrastructure.models.openai_compatible import OpenAICompatibleModelGateway
from ananhu_agent.models.observable_gateway import ObservableModelGateway, TransientSanitizer
from ananhu_agent.ports.model_gateway import (
    ModelErrorCode,
    ModelGatewayError,
    ModelRequest,
    ModelResult,
    ModelUsage,
)
from ananhu_agent.ports.run_event_sink import RunEventSink


def _request() -> ModelRequest:
    return ModelRequest(
        run_id="run_reasoning",
        request_id="req_reasoning",
        session_id="sess_reasoning",
        node_id="understand",
        logical_call_id="run_reasoning:understand:model",
        profile="intent_fast",
        prompt_ref="intent_router.v1",
        prompt="用户咨询工伤认定条件",
        output_schema={
            "type": "object",
            "required": ["intent", "confidence", "slots", "missing_slots", "is_composite"],
            "properties": {
                "intent": {"type": "string"},
                "confidence": {"type": "number"},
                "slots": {"type": "object"},
                "missing_slots": {"type": "array"},
                "is_composite": {"type": "boolean"},
            },
        },
    )


def _valid_output() -> str:
    return json.dumps(
        {
            "intent": "work_injury_recognition",
            "confidence": 0.91,
            "slots": {},
            "missing_slots": [],
            "is_composite": False,
        },
        ensure_ascii=False,
    )


def _call_mock_provider(message: dict) -> ModelResult:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "id": "chatcmpl_reasoning",
                "model": "provider-model-v1",
                "choices": [{"finish_reason": "stop", "message": message}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )
    )
    gateway = OpenAICompatibleModelGateway(
        api_key="contract-key",
        base_url="https://model.example.test/v1",
        model="provider-model",
        transport=transport,
    )
    return asyncio.run(gateway.generate_structured(_request()))


def _model_result(reasoning_content: str | None = None) -> ModelResult:
    return ModelResult(
        output={"intent": "other"},
        provider="provider",
        model="model",
        profile="intent_fast",
        usage=ModelUsage(usage_source="provider", reported=True),
        reasoning_content=reasoning_content,
    )


def test_adapter_returns_explicit_reasoning_string() -> None:
    result = _call_mock_provider(
        message={"content": _valid_output(), "reasoning_content": "分析步骤"}
    )

    assert result.reasoning_content == "分析步骤"


@pytest.mark.parametrize("value, expected", [(None, None), ("", None)])
def test_adapter_normalizes_missing_null_and_empty_reasoning_to_none(
    value: str | None,
    expected: None,
) -> None:
    result = _call_mock_provider(
        message={"content": _valid_output(), "reasoning_content": value}
    )

    assert result.reasoning_content == expected


def test_reasoning_rejects_non_string_provider_value() -> None:
    with pytest.raises(ModelGatewayError) as captured:
        _call_mock_provider(message={"content": _valid_output(), "reasoning_content": {"step": 1}})

    assert captured.value.code is ModelErrorCode.RESPONSE_FORMAT


def test_reasoning_is_excluded_from_dump_and_repr() -> None:
    result = _model_result(reasoning_content="CANARY_REASONING")

    assert "CANARY_REASONING" not in result.model_dump_json()
    assert "CANARY_REASONING" not in repr(result)


def test_reasoning_at_limit_is_not_truncated() -> None:
    sanitizer = TransientSanitizer(reasoning_char_limit=12)

    payload = sanitizer.reasoning("一二三四五六七八九十甲乙")

    assert payload.reasoning_content == "一二三四五六七八九十甲乙"
    assert payload.public_payload == {
        "reasoning_available": True,
        "reasoning_length": 12,
        "reasoning_original_chars": 12,
        "reasoning_truncated": False,
    }


def test_reasoning_over_limit_records_original_length_and_truncation() -> None:
    sanitizer = TransientSanitizer(reasoning_char_limit=5)

    payload = sanitizer.reasoning("abcdefghi")

    assert payload.reasoning_content == "abcde"
    assert len(payload.reasoning_content) <= 5
    assert payload.public_payload == {
        "reasoning_available": True,
        "reasoning_length": 5,
        "reasoning_original_chars": 9,
        "reasoning_truncated": True,
    }


class _CollectingSink(RunEventSink):
    def __init__(self) -> None:
        self.events = []

    def publish(self, event):
        self.events.append(event)


class _SuccessfulGateway:
    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        return _model_result(reasoning_content="CANARY_REASONING")


class _FailingGateway:
    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        raise ModelGatewayError(
            ModelErrorCode.RATE_LIMIT,
            "provider rate limited",
            provider="openai_compatible",
            retryable=True,
            status_code=429,
        )


def test_observable_model_gateway_publishes_transient_reasoning_only() -> None:
    sink = _CollectingSink()
    gateway = ObservableModelGateway(
        _SuccessfulGateway(),
        events=sink,
        sanitizer=TransientSanitizer(reasoning_char_limit=32),
    )

    result = asyncio.run(gateway.generate_structured(_request()))

    assert result.reasoning_content == "CANARY_REASONING"
    assert [event.kind for event in sink.events] == ["model_started", "model_finished"]
    finished = sink.events[-1]
    assert finished.transient_payload.reasoning_content == "CANARY_REASONING"
    assert finished.public_payload.reasoning_available is True
    assert finished.public_payload.reasoning_length == len("CANARY_REASONING")
    assert "CANARY_REASONING" not in finished.to_trace_event().model_dump_json()


def test_observable_model_gateway_publishes_failed_event() -> None:
    sink = _CollectingSink()
    gateway = ObservableModelGateway(
        _FailingGateway(),
        events=sink,
        sanitizer=TransientSanitizer(),
    )

    with pytest.raises(ModelGatewayError):
        asyncio.run(gateway.generate_structured(_request()))

    assert [event.kind for event in sink.events] == ["model_started", "model_failed"]
    assert sink.events[-1].public_payload.error_code == "rate_limit_error"
