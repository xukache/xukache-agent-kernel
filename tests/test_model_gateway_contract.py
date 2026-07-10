from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest

from ananhu_agent.infrastructure.models.fake import FakeModelGateway
from ananhu_agent.infrastructure.models.openai_compatible import OpenAICompatibleModelGateway
from ananhu_agent.ports.model_gateway import (
    ModelErrorCode,
    ModelGatewayError,
    ModelRequest,
)


def _request(prompt: str = "四川十级工伤，月工资6000，大概能赔多少钱？") -> ModelRequest:
    return ModelRequest(
        run_id="run_model_contract",
        request_id="req_model_contract",
        node_id="understand",
        logical_call_id="run_model_contract:understand:model",
        profile="intent_fast",
        prompt_ref="intent_router.v1",
        prompt=prompt,
        output_schema={
            "type": "object",
            "required": ["intent", "confidence", "slots", "missing_slots", "is_composite"],
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [
                        "work_injury_recognition", "labor_capacity",
                        "insurance_participation", "payment_calculation", "other",
                    ],
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "slots": {"type": "object"},
                "missing_slots": {"type": "array", "items": {"type": "string"}},
                "is_composite": {"type": "boolean"},
            },
        },
    )


def test_fake_gateway_returns_project_result_and_fake_usage() -> None:
    result = asyncio.run(FakeModelGateway().generate_structured(_request()))

    assert result.output["intent"] == "payment_calculation"
    assert result.output["slots"]["province"] == "四川省"
    assert result.provider == "fake"
    assert result.usage.usage_source == "fake"
    assert result.usage.total_tokens == 0
    assert result.usage.estimated_cost is None


def test_openai_compatible_gateway_parses_structured_output_and_usage() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_contract",
                "model": "provider-model-v1",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "intent": "payment_calculation",
                                    "confidence": 0.96,
                                    "slots": {"province": "四川省"},
                                    "missing_slots": [],
                                    "is_composite": False,
                                },
                                ensure_ascii=False,
                            )
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 30,
                    "total_tokens": 150,
                    "prompt_tokens_details": {"cached_tokens": 20},
                },
            },
        )

    transport = httpx.MockTransport(handler)
    gateway = OpenAICompatibleModelGateway(
        api_key="secret-contract-key",
        base_url="https://model.example.test/v1",
        model="provider-model",
        temperature=0.35,
        transport=transport,
    )

    result = asyncio.run(gateway.generate_structured(_request()))

    assert captured["url"] == "https://model.example.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer secret-contract-key"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert "JSON" in captured["body"]["messages"][0]["content"]
    assert '"output_schema"' in captured["body"]["messages"][0]["content"]
    assert '"missing_slots"' in captured["body"]["messages"][0]["content"]
    assert captured["body"]["temperature"] == 0.35
    assert result.output["intent"] == "payment_calculation"
    assert result.provider == "openai_compatible"
    assert result.model == "provider-model-v1"
    assert result.usage.input_tokens == 120
    assert result.usage.output_tokens == 30
    assert result.usage.cache_tokens == 20
    assert result.usage.total_tokens == 150
    assert result.usage.usage_source == "provider"


def test_openai_compatible_gateway_normalizes_authentication_error_without_secret() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": {"message": "invalid api key"}})
    )
    gateway = OpenAICompatibleModelGateway(
        api_key="must-not-appear",
        base_url="https://model.example.test/v1",
        model="provider-model",
        transport=transport,
    )

    with pytest.raises(ModelGatewayError) as captured:
        asyncio.run(gateway.generate_structured(_request()))

    assert captured.value.code is ModelErrorCode.AUTHENTICATION
    assert captured.value.status_code == 401
    assert captured.value.retryable is False
    assert "must-not-appear" not in str(captured.value)


def test_openai_compatible_gateway_rejects_non_json_content() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "model": "provider-model",
                "choices": [{"finish_reason": "stop", "message": {"content": "not-json"}}],
                "usage": {},
            },
        )
    )
    gateway = OpenAICompatibleModelGateway(
        api_key="contract-key",
        base_url="https://model.example.test/v1",
        model="provider-model",
        transport=transport,
    )

    with pytest.raises(ModelGatewayError) as captured:
        asyncio.run(gateway.generate_structured(_request()))

    assert captured.value.code is ModelErrorCode.RESPONSE_FORMAT


def test_openai_compatible_gateway_rejects_output_that_violates_schema() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "model": "provider-model",
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({
                        "intent": "invented_intent",
                        "confidence": "high",
                        "slots": [],
                        "missing_slots": {},
                        "is_composite": "no",
                    })},
                }],
                "usage": {},
            },
        )
    )
    gateway = OpenAICompatibleModelGateway(
        api_key="contract-key",
        base_url="https://model.example.test/v1",
        model="provider-model",
        transport=transport,
    )

    with pytest.raises(ModelGatewayError) as captured:
        asyncio.run(gateway.generate_structured(_request()))

    assert captured.value.code is ModelErrorCode.OUTPUT_SCHEMA


@pytest.mark.parametrize("usage", [None, {"prompt_tokens": "not-a-number"}])
def test_openai_compatible_gateway_normalizes_invalid_usage(usage) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "model": "provider-model",
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({
                        "intent": "other",
                        "confidence": 0.8,
                        "slots": {},
                        "missing_slots": [],
                        "is_composite": False,
                    })},
                }],
                "usage": usage,
            },
        )
    )
    gateway = OpenAICompatibleModelGateway(
        api_key="contract-key",
        base_url="https://model.example.test/v1",
        model="provider-model",
        transport=transport,
    )

    with pytest.raises(ModelGatewayError) as captured:
        asyncio.run(gateway.generate_structured(_request()))

    assert captured.value.code is ModelErrorCode.RESPONSE_FORMAT


def test_real_model_smoke_is_explicit_opt_in() -> None:
    if os.getenv("ANANHU_REAL_MODEL_SMOKE") != "1":
        pytest.skip("设置 ANANHU_REAL_MODEL_SMOKE=1 后才运行真实模型 smoke")

    api_key = os.getenv("ANANHU_MODEL_API_KEY")
    base_url = os.getenv("ANANHU_MODEL_BASE_URL")
    model = os.getenv("ANANHU_REAL_MODEL")
    if not api_key or not base_url or not model:
        pytest.skip("真实模型 smoke 缺少 API key、base URL 或 model")

    gateway = OpenAICompatibleModelGateway(api_key=api_key, base_url=base_url, model=model)
    result = asyncio.run(gateway.generate_structured(_request("用户咨询工伤认定条件")))

    assert result.output["intent"] in {
        "work_injury_recognition",
        "labor_capacity",
        "insurance_participation",
        "payment_calculation",
        "other",
    }
    assert result.usage.usage_source == "provider"
