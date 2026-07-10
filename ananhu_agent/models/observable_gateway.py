from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from ananhu_agent.ports.model_gateway import (
    ModelGateway,
    ModelGatewayError,
    ModelRequest,
    ModelResult,
)
from ananhu_agent.ports.run_event_sink import (
    ModelFailedEvent,
    ModelFailedPayload,
    ModelFinishedEvent,
    ModelFinishedPayload,
    ModelStartedEvent,
    ModelStartedPayload,
    RunEventSink,
    RunTransientPayload,
)


@dataclass(frozen=True)
class SanitizedReasoning:
    """reasoning 的展示投影；公共字段可落 trace，正文只留在瞬态 payload。"""

    reasoning_content: str | None
    public_payload: dict[str, int | bool]


class TransientSanitizer:
    """裁剪模型瞬态内容，避免 prompt/reasoning 进入持久化投影。"""

    def __init__(self, reasoning_char_limit: int = 4000) -> None:
        self.reasoning_char_limit = reasoning_char_limit

    def model_input(self, request: ModelRequest) -> dict[str, object]:
        return {
            "prompt_ref": request.prompt_ref,
            "profile": request.profile,
            "schema_keys": sorted(request.output_schema.get("properties", {})),
        }

    def model_output(self, result: ModelResult) -> dict[str, object]:
        return {
            "output_keys": sorted(result.output),
            "finish_reason": result.finish_reason,
        }

    def reasoning(self, reasoning_content: str | None) -> SanitizedReasoning:
        if not reasoning_content:
            return SanitizedReasoning(
                reasoning_content=None,
                public_payload={
                    "reasoning_available": False,
                    "reasoning_length": 0,
                    "reasoning_original_chars": 0,
                    "reasoning_truncated": False,
                },
            )
        original_chars = len(reasoning_content)
        truncated = original_chars > self.reasoning_char_limit
        display = reasoning_content[: self.reasoning_char_limit] if truncated else reasoning_content
        return SanitizedReasoning(
            reasoning_content=display,
            public_payload={
                "reasoning_available": True,
                "reasoning_length": len(display),
                "reasoning_original_chars": original_chars,
                "reasoning_truncated": truncated,
            },
        )


class ObservableModelGateway:
    """为任意 ModelGateway 增加框架中立实时模型生命周期事件。"""

    def __init__(
        self,
        inner: ModelGateway,
        *,
        events: RunEventSink,
        sanitizer: TransientSanitizer,
    ) -> None:
        self.inner = inner
        self.events = events
        self.sanitizer = sanitizer

    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        started = perf_counter()
        fields = _event_fields(request)
        self.events.publish(ModelStartedEvent(
            **fields,
            public_payload=ModelStartedPayload(
                profile=request.profile,
                prompt_ref=request.prompt_ref,
                input_summary=self.sanitizer.model_input(request),
            ),
        ))
        try:
            result = await self.inner.generate_structured(request)
        except ModelGatewayError as exc:
            self.events.publish(ModelFailedEvent(
                **fields,
                public_payload=ModelFailedPayload(
                    profile=request.profile,
                    provider=exc.provider,
                    error_code=exc.code.value,
                    retryable=exc.retryable,
                    status_code=exc.status_code,
                    latency_ms=int((perf_counter() - started) * 1000),
                    error_message=type(exc).__name__,
                ),
            ))
            raise

        reasoning = self.sanitizer.reasoning(result.reasoning_content)
        self.events.publish(ModelFinishedEvent(
            **fields,
            public_payload=ModelFinishedPayload(
                profile=result.profile,
                provider=result.provider,
                model=result.model,
                finish_reason=result.finish_reason,
                usage=result.usage.model_dump(mode="json"),
                output_summary=self.sanitizer.model_output(result),
                latency_ms=result.latency_ms or int((perf_counter() - started) * 1000),
                **reasoning.public_payload,
            ),
            transient_payload=RunTransientPayload(reasoning_content=reasoning.reasoning_content),
        ))
        return result


def _event_fields(request: ModelRequest) -> dict[str, object]:
    return {
        "run_id": request.run_id,
        "request_id": request.request_id,
        "session_id": request.session_id,
        "node_id": request.node_id,
        "logical_call_id": request.logical_call_id,
        "attempt": request.attempt,
    }
