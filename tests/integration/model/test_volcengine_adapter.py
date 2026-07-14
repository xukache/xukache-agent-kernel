"""B3 Volcengine Ark Adapter 的确定性 HTTP 集成测试。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from adapters.model.volcengine import VolcengineArkConfig, VolcengineArkModel
from agent_kernel.model import (
    FinishReason,
    Model,
    ModelError,
    ModelErrorCode,
    ModelRequest,
)


def _config() -> VolcengineArkConfig:
    return VolcengineArkConfig(
        api_key="test-key",
        model="test-model",
        base_url="https://ark.example.test/api/v3",
    )


def test_config_reads_yaml_catalog_and_provider_key_without_exposing_secret(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "models.yaml"
    catalog.write_text(
        """
version: 1
default:
  provider: volcengine
  model: configured-model
providers:
  volcengine:
    adapter: volcengine_ark
    api_key_env: VOLCENGINE_API_KEY
    base_url: https://catalog.example.test/api/v3
    timeout_seconds: 12
    models:
      configured-model:
        capabilities: [generate]
""",
        encoding="utf-8",
    )

    config = VolcengineArkConfig.from_yaml(
        str(catalog),
        {"VOLCENGINE_API_KEY": "test-key"},
    )

    assert config.model == "configured-model"
    assert config.api_key == "test-key"
    assert config.base_url == "https://catalog.example.test/api/v3"
    assert config.timeout_seconds == 12
    assert "test-key" not in repr(config)


def test_config_fails_before_network_when_catalog_or_key_is_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="catalog does not exist"):
        VolcengineArkConfig.from_yaml(str(tmp_path / "missing.yaml"), {})

    catalog = tmp_path / "models.yaml"
    catalog.write_text(
        """
version: 1
default: {provider: volcengine, model: configured-model}
providers:
  volcengine:
    adapter: volcengine_ark
    api_key_env: VOLCENGINE_API_KEY
    base_url: https://catalog.example.test/api/v3
    models: {configured-model: {}}
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="VOLCENGINE_API_KEY"):
        VolcengineArkConfig.from_yaml(str(catalog), {})


def test_config_from_environment_uses_catalog_path_override(
    tmp_path: Path,
) -> None:
    catalog = tmp_path / "models.yaml"
    catalog.write_text(
        """
version: 1
default: {provider: volcengine, model: configured-model}
providers:
  volcengine:
    adapter: volcengine_ark
    api_key_env: VOLCENGINE_API_KEY
    base_url: https://catalog.example.test/api/v3
    models: {configured-model: {}}
""",
        encoding="utf-8",
    )

    config = VolcengineArkConfig.from_environment(
        {
            "ANANHU_MODEL_CATALOG": str(catalog),
            "VOLCENGINE_API_KEY": "test-key",
        }
    )

    assert config.model == "configured-model"
    assert config.base_url == "https://catalog.example.test/api/v3"


def test_generate_maps_chat_response_to_model_response() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "request-1",
                "model": "test-model",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "42"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 2,
                    "total_tokens": 7,
                },
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = VolcengineArkModel(_config(), client=client)

    try:
        response = asyncio.run(model.generate(ModelRequest(input="18 + 24")))
    finally:
        asyncio.run(client.aclose())

    assert response.text == "42"
    assert response.finish_reason is FinishReason.STOP
    assert response.usage.input_tokens == 5
    assert response.provider_metadata == {"request_id": "request-1"}
    assert captured["authorization"] == "Bearer test-key"
    assert captured["body"]["model"] == "test-model"  # type: ignore[index]


def test_generate_uses_configured_base_url() -> None:
    captured_url: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_url.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "id": "request-1",
                "model": "test-model",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = VolcengineArkModel(
        VolcengineArkConfig(
            api_key="test-key",
            model="test-model",
            base_url="https://proxy.example.test/api/v3",
        ),
        client=client,
    )

    try:
        asyncio.run(model.generate(ModelRequest(input="hello")))
    finally:
        asyncio.run(client.aclose())

    assert captured_url == ["https://proxy.example.test/api/v3/chat/completions"]


def test_adapter_implements_model_protocol_and_declares_capabilities() -> None:
    model = VolcengineArkModel(_config())

    assert isinstance(model, Model)
    assert model.capabilities == frozenset({"generate"})

    with pytest.raises(ModelError) as error_info:
        model.stream(ModelRequest(input="hello"))

    assert error_info.value.code is ModelErrorCode.PROVIDER


def test_generate_maps_rate_limit_and_timeout_errors() -> None:
    def rate_limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "slow down"}})

    rate_client = httpx.AsyncClient(transport=httpx.MockTransport(rate_limit_handler))
    rate_model = VolcengineArkModel(_config(), client=rate_client)

    try:
        with pytest.raises(ModelError) as error_info:
            asyncio.run(rate_model.generate(ModelRequest(input="hello")))
    finally:
        asyncio.run(rate_client.aclose())

    assert error_info.value.code is ModelErrorCode.RATE_LIMIT
    assert error_info.value.retryable is True

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    timeout_client = httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler))
    timeout_model = VolcengineArkModel(_config(), client=timeout_client)

    try:
        with pytest.raises(ModelError) as error_info:
            asyncio.run(timeout_model.generate(ModelRequest(input="hello")))
    finally:
        asyncio.run(timeout_client.aclose())

    assert error_info.value.code is ModelErrorCode.TIMEOUT
    assert error_info.value.retryable is True
