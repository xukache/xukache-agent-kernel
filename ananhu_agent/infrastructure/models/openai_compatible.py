from __future__ import annotations

import json
from time import monotonic
from typing import Any

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from ananhu_agent.ports.model_gateway import (
    ModelErrorCode,
    ModelGatewayError,
    ModelRequest,
    ModelResult,
    ModelUsage,
)


class OpenAICompatibleModelGateway:
    """适配 OpenAI-compatible Chat Completions 的最小结构化调用子集。"""

    provider = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        input_cost_per_million: float | None = None,
        output_cost_per_million: float | None = None,
        currency: str = "USD",
    ) -> None:
        if not api_key or not base_url or not model:
            raise ModelGatewayError(
                ModelErrorCode.CONFIGURATION,
                "OpenAI-compatible provider 配置不完整",
                provider=self.provider,
                retryable=False,
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._input_cost_per_million = input_cost_per_million
        self._output_cost_per_million = output_cost_per_million
        self._currency = currency

    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        started_at = monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        # 部分 OpenAI-compatible provider 要求消息显式包含 JSON 关键字。
                        "messages": [{
                            "role": "user",
                            "content": _json_prompt(request.prompt, request.output_schema),
                        }],
                        "temperature": (
                            request.temperature
                            if request.temperature is not None
                            else self._temperature
                        ),
                        "response_format": {"type": "json_object"},
                    },
                )
        except httpx.TimeoutException as exc:
            raise ModelGatewayError(
                ModelErrorCode.TIMEOUT,
                "模型请求超时",
                provider=self.provider,
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise ModelGatewayError(
                ModelErrorCode.PROVIDER,
                "模型网络请求失败",
                provider=self.provider,
                retryable=True,
            ) from exc

        if response.status_code >= 400:
            raise _http_error(response.status_code)

        payload = _response_payload(response)
        output = _structured_output(payload)
        _validate_structured_output(output, request.output_schema)
        usage = _usage_from_payload(
            payload.get("usage", {}),
            input_cost_per_million=self._input_cost_per_million,
            output_cost_per_million=self._output_cost_per_million,
            currency=self._currency,
        )
        choice = payload["choices"][0]
        return ModelResult(
            output=output,
            provider=self.provider,
            model=str(payload.get("model") or self._model),
            profile=request.profile,
            finish_reason=choice.get("finish_reason"),
            provider_request_id=payload.get("id"),
            usage=usage,
            latency_ms=max(0, int((monotonic() - started_at) * 1000)),
            attempt=request.attempt,
        )


def _json_prompt(prompt: str, output_schema: dict[str, Any]) -> str:
    schema = json.dumps({"output_schema": output_schema}, ensure_ascii=False)
    return (
        f"{prompt}\n\n严格按照以下 JSON Schema 输出合法 JSON 对象，"
        f"不要输出 Markdown 或额外说明：\n{schema}"
    )


def _http_error(status_code: int) -> ModelGatewayError:
    if status_code in {401, 403}:
        code, retryable = ModelErrorCode.AUTHENTICATION, False
    elif status_code == 429:
        code, retryable = ModelErrorCode.RATE_LIMIT, True
    else:
        code, retryable = ModelErrorCode.PROVIDER, status_code >= 500
    return ModelGatewayError(
        code,
        f"模型 provider 返回 HTTP {status_code}",
        provider=OpenAICompatibleModelGateway.provider,
        retryable=retryable,
        status_code=status_code,
    )


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ModelGatewayError(
            ModelErrorCode.RESPONSE_FORMAT,
            "模型响应不是合法 JSON",
            provider=OpenAICompatibleModelGateway.provider,
            retryable=False,
        ) from exc
    if not isinstance(payload, dict):
        raise ModelGatewayError(
            ModelErrorCode.RESPONSE_FORMAT,
            "模型响应顶层必须是对象",
            provider=OpenAICompatibleModelGateway.provider,
            retryable=False,
        )
    return payload


def _structured_output(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        content = payload["choices"][0]["message"]["content"]
        output = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ModelGatewayError(
            ModelErrorCode.RESPONSE_FORMAT,
            "模型响应缺少合法的结构化 content",
            provider=OpenAICompatibleModelGateway.provider,
            retryable=False,
        ) from exc
    if not isinstance(output, dict):
        raise ModelGatewayError(
            ModelErrorCode.RESPONSE_FORMAT,
            "模型结构化输出必须是对象",
            provider=OpenAICompatibleModelGateway.provider,
            retryable=False,
        )
    return output


def _validate_structured_output(output: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(output)
    except SchemaError as exc:
        raise ModelGatewayError(
            ModelErrorCode.CONFIGURATION,
            "项目模型输出 schema 非法",
            provider=OpenAICompatibleModelGateway.provider,
            retryable=False,
        ) from exc
    except ValidationError as exc:
        raise ModelGatewayError(
            ModelErrorCode.OUTPUT_SCHEMA,
            "模型输出不符合项目 schema",
            provider=OpenAICompatibleModelGateway.provider,
            retryable=False,
        ) from exc


def _usage_from_payload(
    raw: Any,
    *,
    input_cost_per_million: float | None,
    output_cost_per_million: float | None,
    currency: str,
) -> ModelUsage:
    try:
        if not isinstance(raw, dict):
            raise TypeError("usage must be an object")
        input_tokens = int(raw.get("prompt_tokens") or 0)
        output_tokens = int(raw.get("completion_tokens") or 0)
        total_tokens = int(raw.get("total_tokens") or input_tokens + output_tokens)
        details = raw.get("prompt_tokens_details") or {}
        if not isinstance(details, dict):
            raise TypeError("prompt_tokens_details must be an object")
        cache_tokens = int(details.get("cached_tokens") or 0)
    except (TypeError, ValueError) as exc:
        raise ModelGatewayError(
            ModelErrorCode.RESPONSE_FORMAT,
            "模型 usage 字段格式非法",
            provider=OpenAICompatibleModelGateway.provider,
            retryable=False,
        ) from exc
    estimated_cost = None
    if input_cost_per_million is not None and output_cost_per_million is not None:
        estimated_cost = round(
            (input_tokens * input_cost_per_million + output_tokens * output_cost_per_million)
            / 1_000_000,
            8,
        )
    return ModelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_tokens=cache_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        currency=currency if estimated_cost is not None else None,
        usage_source="provider",
    )
