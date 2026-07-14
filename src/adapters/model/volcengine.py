"""Volcengine Ark 的 Model Protocol Adapter。

本模块只负责环境配置、HTTP 请求转换和响应归一化。Volcengine 的请求对象、
凭证和 HTTP 错误不能进入 agent_kernel。
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from collections.abc import AsyncIterator
from typing import cast

import httpx
import yaml
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import SchemaError as JsonSchemaError
from jsonschema import validate as validate_json_schema

from agent_kernel.model import (
    FinishReason,
    Model,
    ModelError,
    ModelErrorCode,
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
    ToolCall,
    ToolCallDelta,
    Usage,
)
from agent_kernel.model.schemas import JsonObject, JsonValue


@dataclass(frozen=True, slots=True, kw_only=True)
class VolcengineArkConfig:
    """Volcengine Ark Adapter 的运行配置，不进入 Kernel Schema。"""

    api_key: str = field(repr=False)
    model: str
    base_url: str
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("VOLCENGINE_API_KEY must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.base_url.strip():
            raise ValueError("base_url must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    @classmethod
    def from_yaml(
        cls,
        catalog_path: str,
        environ: Mapping[str, str] | None = None,
    ) -> VolcengineArkConfig:
        """从 YAML Model Catalog 读取配置，环境变量只提供 YAML 指定的密钥。"""
        values = environ if environ is not None else os.environ
        try:
            with open(catalog_path, encoding="utf-8") as stream:
                catalog = yaml.safe_load(stream)
        except FileNotFoundError as exc:
            raise ValueError(f"model catalog does not exist: {catalog_path}") from exc
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid model catalog: {catalog_path}") from exc

        if not isinstance(catalog, dict):
            raise ValueError("model catalog root must be a mapping")
        if catalog.get("version") != 1:
            raise ValueError("model catalog version must be 1")
        default = catalog.get("default")
        providers = catalog.get("providers")
        if not isinstance(default, dict) or not isinstance(providers, dict):
            raise ValueError("model catalog requires default and providers mappings")

        provider_name = default.get("provider")
        model_name = default.get("model")
        provider = providers.get(provider_name)
        if not isinstance(provider_name, str) or not isinstance(model_name, str):
            raise ValueError("model catalog default must define provider and model")
        if not isinstance(provider, dict):
            raise ValueError(f"provider is not configured: {provider_name}")
        if provider.get("adapter") != "volcengine_ark":
            raise ValueError(f"unsupported Volcengine adapter: {provider.get('adapter')}")

        models = provider.get("models")
        api_key_env = provider.get("api_key_env")
        base_url = provider.get("base_url")
        timeout_seconds = provider.get("timeout_seconds", 30.0)
        if not isinstance(models, dict) or model_name not in models:
            raise ValueError(f"model is not configured: {model_name}")
        if not isinstance(api_key_env, str) or not api_key_env:
            raise ValueError("provider api_key_env must be configured")
        if not isinstance(base_url, str) or not base_url:
            raise ValueError("provider base_url must be configured")
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("provider timeout_seconds must be positive")

        api_key = values.get(api_key_env, "")
        if not api_key:
            raise ValueError(f"{api_key_env} is required")
        return cls(
            api_key=api_key,
            model=model_name,
            base_url=base_url,
            timeout_seconds=float(timeout_seconds),
        )

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> VolcengineArkConfig:
        """从环境变量定位 YAML，具体 Provider 配置仍由 YAML 管理。"""
        values = environ if environ is not None else os.environ
        catalog_path = values.get("ANANHU_MODEL_CATALOG", "config/models.yaml")
        return cls.from_yaml(catalog_path, values)


class VolcengineArkModel:
    """通过 Ark Chat Completions HTTP 接口实现 Model Protocol。"""

    def __init__(
        self,
        config: VolcengineArkConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client

    @property
    def capabilities(self) -> frozenset[str]:
        """当前 Adapter 支持完整生成和 SSE Streaming。"""
        return frozenset({"generate", "stream"})

    async def generate(self, request: ModelRequest) -> ModelResponse:
        payload = self._build_payload(request)
        response = await self._post(payload)
        return self._parse_response(response, request.output_schema)

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        """返回一次性消费的 Provider Neutral SSE 增量流。"""
        return self._stream(request)

    async def _stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        payload = self._build_payload(request)
        payload["stream"] = True
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                async with self._client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
                ) as response:
                    self._raise_for_status(response)
                    async for chunk in self._parse_stream(
                        response,
                        request.output_schema,
                    ):
                        yield chunk
            else:
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds
                ) as client:
                    async with client.stream(
                        "POST",
                        url,
                        headers=headers,
                        json=payload,
                    ) as response:
                        self._raise_for_status(response)
                        async for chunk in self._parse_stream(
                            response,
                            request.output_schema,
                        ):
                            yield chunk
        except ModelError:
            raise
        except httpx.TimeoutException as exc:
            raise ModelError(
                ModelErrorCode.TIMEOUT,
                "Volcengine streaming request timed out",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ModelError(
                ModelErrorCode.PROVIDER,
                "Volcengine streaming request failed",
                retryable=True,
            ) from exc

    def _build_payload(self, request: ModelRequest) -> JsonObject:
        payload: JsonObject = {
            "model": self._config.model,
            "messages": self._build_messages(request),
        }
        if request.tool_schemas:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in request.tool_schemas
            ]
        if request.output_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "model_output",
                    "schema": request.output_schema,
                    "strict": True,
                },
            }
        return payload

    @staticmethod
    def _build_messages(request: ModelRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.instructions:
            messages.append({"role": "system", "content": request.instructions})
        messages.extend(
            {
                "role": message.role.value,
                "content": _content_to_text(message.content),
            }
            for message in request.context
        )
        for memory in request.memory_items:
            messages.append(
                {
                    "role": "system",
                    "content": f"[memory:{memory.memory_id}] {memory.content}",
                }
            )
        messages.append(
            {
                "role": "user",
                "content": _content_to_text(request.input),
            }
        )
        return messages

    async def _post(self, payload: JsonObject) -> httpx.Response:
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                response = await self._client.post(url, headers=headers, json=payload)
            else:
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds
                ) as client:
                    response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ModelError(
                ModelErrorCode.TIMEOUT,
                "Volcengine request timed out",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ModelError(
                ModelErrorCode.PROVIDER,
                "Volcengine request failed",
                retryable=True,
            ) from exc

        self._raise_for_status(response)
        return response

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 429:
            raise ModelError(
                ModelErrorCode.RATE_LIMIT,
                "Volcengine rate limit reached",
                retryable=True,
                details={"status_code": response.status_code},
            )
        if response.status_code in {400, 422}:
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine rejected the request format",
                details={"status_code": response.status_code},
            )
        if response.status_code >= 400:
            raise ModelError(
                ModelErrorCode.PROVIDER,
                "Volcengine returned an error",
                details={"status_code": response.status_code},
            )

    async def _parse_stream(
        self,
        response: httpx.Response,
        output_schema: JsonObject | None,
    ) -> AsyncIterator[ModelStreamChunk]:
        structured_fragments: list[str] = []
        finish_reason: FinishReason | None = None
        model_id = self._config.model
        saw_done = False

        async for line in response.aiter_lines():
            line = line.strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                saw_done = True
                break

            try:
                body = json.loads(data)
                if not isinstance(body, dict):
                    raise TypeError("stream event must be an object")
                raw_model_id = body.get("model")
                if isinstance(raw_model_id, str):
                    model_id = raw_model_id
                choices = body["choices"]
                if not isinstance(choices, list) or not choices:
                    raise TypeError("stream choices must be a non-empty list")
                choice = choices[0]
                if not isinstance(choice, dict):
                    raise TypeError("stream choice must be an object")
                delta = choice.get("delta", {})
                if not isinstance(delta, dict):
                    raise TypeError("stream delta must be an object")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ModelError(
                    ModelErrorCode.FORMAT,
                    "Volcengine stream event does not match the expected format",
                ) from exc

            raw_finish_reason = choice.get("finish_reason")
            event_finish_reason = (
                self._parse_finish_reason(raw_finish_reason)
                if raw_finish_reason is not None
                else None
            )
            if event_finish_reason is not None:
                finish_reason = event_finish_reason

            usage = (
                self._parse_usage(body["usage"])
                if isinstance(body.get("usage"), dict)
                else None
            )
            content = delta.get("content")
            if content is not None and not isinstance(content, str):
                raise ModelError(
                    ModelErrorCode.FORMAT,
                    "Volcengine stream content is not text",
                )

            if output_schema is not None and content:
                structured_fragments.append(content)

            tool_deltas = self._parse_tool_call_deltas(delta.get("tool_calls"))
            if output_schema is None and content:
                yield ModelStreamChunk(
                    text_delta=content,
                    usage=usage,
                    finish_reason=event_finish_reason,
                    model_id=model_id,
                )
                usage = None
                event_finish_reason = None

            for tool_delta in tool_deltas:
                yield ModelStreamChunk(
                    tool_call_delta=tool_delta,
                    model_id=model_id,
                )

            if event_finish_reason is not None:
                if output_schema is not None:
                    structured_output = self._parse_structured_output(
                        "".join(structured_fragments),
                        output_schema,
                    )
                    yield ModelStreamChunk(
                        structured_delta=structured_output,
                        model_id=model_id,
                    )
                yield ModelStreamChunk(
                    usage=usage,
                    finish_reason=event_finish_reason,
                    model_id=model_id,
                )
            elif usage is not None and not content and not tool_deltas:
                yield ModelStreamChunk(usage=usage, model_id=model_id)

        if not saw_done or finish_reason is None:
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine stream ended without a finish reason",
            )

    @staticmethod
    def _parse_tool_call_deltas(value: JsonValue) -> tuple[ToolCallDelta, ...]:
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine stream tool_calls is not a list",
            )

        deltas: list[ToolCallDelta] = []
        try:
            for item in value:
                if not isinstance(item, dict):
                    raise TypeError("tool call delta is not an object")
                function = item.get("function", {})
                if not isinstance(function, dict):
                    raise TypeError("tool call delta function is not an object")
                call_id = item.get("id")
                name = function.get("name")
                arguments_delta = function.get("arguments")
                if call_id is not None and not isinstance(call_id, str):
                    raise TypeError("tool call delta id is not text")
                if name is not None and not isinstance(name, str):
                    raise TypeError("tool call delta name is not text")
                if arguments_delta is not None and not isinstance(
                    arguments_delta,
                    str,
                ):
                    raise TypeError("tool call delta arguments are not text")
                deltas.append(
                    ToolCallDelta(
                        call_id=call_id,
                        name=name,
                        arguments_delta=arguments_delta,
                    )
                )
        except (TypeError, ValueError) as exc:
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine stream tool call does not match the expected format",
            ) from exc
        return tuple(deltas)

    def _parse_response(
        self,
        response: httpx.Response,
        output_schema: JsonObject | None,
    ) -> ModelResponse:
        try:
            body = cast(JsonObject, response.json())
            choices = body["choices"]
            if not isinstance(choices, list) or not choices:
                raise ValueError("choices is empty")
            choice = choices[0]
            if not isinstance(choice, dict):
                raise ValueError("choice is not an object")
            message = choice["message"]
            if not isinstance(message, dict):
                raise ValueError("message is not an object")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine response does not match the expected format",
            ) from exc

        raw_tool_calls = message.get("tool_calls", [])
        if not isinstance(raw_tool_calls, list):
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine tool_calls is not a list",
            )
        tool_calls = tuple(self._parse_tool_call(item) for item in raw_tool_calls)
        finish_reason = self._parse_finish_reason(choice.get("finish_reason"))
        content = message.get("content")
        text = content if isinstance(content, str) else None
        structured_output = content if isinstance(content, dict) else None
        if output_schema is not None:
            structured_output = self._parse_structured_output(content, output_schema)
            text = None
        model_id = body.get("model") or self._config.model
        provider_metadata = (
            {"request_id": body["id"]} if isinstance(body.get("id"), str) else {}
        )

        return ModelResponse(
            text=text,
            structured_output=structured_output,
            tool_calls=tool_calls,
            usage=self._parse_usage(body.get("usage")),
            finish_reason=finish_reason,
            model_id=model_id,
            provider_metadata=provider_metadata,
        )

    @staticmethod
    def _parse_structured_output(
        content: JsonValue,
        output_schema: JsonObject,
    ) -> JsonObject:
        """把 Provider 内容转换为对象并在 Adapter 边界完成 Schema 校验。"""
        try:
            if isinstance(content, str):
                content = json.loads(content)
            if not isinstance(content, dict):
                raise TypeError("structured output must be a JSON object")
            validate_json_schema(instance=content, schema=output_schema)
        except (
            JsonSchemaError,
            JsonSchemaValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine structured output does not match the requested schema",
            ) from exc
        return content

    @staticmethod
    def _parse_tool_call(item: JsonValue) -> ToolCall:
        try:
            if not isinstance(item, dict):
                raise TypeError("tool call is not an object")
            function = item["function"]
            if not isinstance(function, dict):
                raise TypeError("tool function is not an object")
            arguments = function["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if not isinstance(arguments, dict):
                raise TypeError("tool arguments are not an object")
            call_id = item["id"]
            name = function["name"]
            if not isinstance(call_id, str) or not isinstance(name, str):
                raise TypeError("tool call identity is invalid")
            return ToolCall(
                call_id=call_id,
                name=name,
                arguments=arguments,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine tool call does not match the expected format",
            ) from exc

    @staticmethod
    def _parse_finish_reason(value: JsonValue) -> FinishReason:
        mapping = {
            "stop": FinishReason.STOP,
            "tool_calls": FinishReason.TOOL_CALL,
            "tool_call": FinishReason.TOOL_CALL,
            "length": FinishReason.LENGTH,
            "content_filter": FinishReason.CONTENT_FILTER,
        }
        if not isinstance(value, str) or value not in mapping:
            raise ModelError(
                ModelErrorCode.FORMAT,
                "Volcengine returned an unsupported finish reason",
            )
        return mapping[value]

    @staticmethod
    def _parse_usage(value: JsonValue) -> Usage:
        if not isinstance(value, dict):
            return Usage()
        return Usage(
            input_tokens=value.get("prompt_tokens"),
            output_tokens=value.get("completion_tokens"),
            total_tokens=value.get("total_tokens"),
        )


def _content_to_text(value: str | JsonObject) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
