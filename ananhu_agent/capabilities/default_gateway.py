from __future__ import annotations

import asyncio
from copy import deepcopy
import inspect
from time import perf_counter

from ananhu_agent.capabilities.contracts import (
    CapabilityError,
    CapabilityGateway,
    CapabilityIdempotency,
    CapabilityPolicy,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
)
from ananhu_agent.capabilities.registry import CapabilityDefinition, CapabilityRegistry
from ananhu_agent.ports.run_event_sink import (
    CapabilityFailedEvent,
    CapabilityFailedPayload,
    CapabilityFinishedEvent,
    CapabilityFinishedPayload,
    CapabilityStartedEvent,
    CapabilityStartedPayload,
    NoOpRunEventSink,
    RunEventSink,
)


class DefaultCapabilityGateway(CapabilityGateway):
    """直接执行显式注册能力，并集中承担能力治理。"""

    def __init__(
        self,
        registry: CapabilityRegistry,
        *,
        event_sink: RunEventSink | None = None,
        trace_recorder=None,
    ) -> None:
        self.registry = registry
        self.event_sink = event_sink or NoOpRunEventSink()
        self.trace_recorder = trace_recorder
        self._results_by_logical_call_id: dict[
            tuple[str, str], CapabilityResult
        ] = {}
        self._request_signatures: dict[tuple[str, str], tuple[str, str, dict]] = {}
        self._locks_by_logical_call_id: dict[tuple[str, str], asyncio.Lock] = {}

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        started = perf_counter()
        event_fields = {
            "run_id": request.run_id,
            "request_id": request.request_id,
            "session_id": request.session_id,
            "runtime_name": request.runtime_name,
            "runtime_version": request.runtime_version,
            "node_id": request.node_id,
            "logical_call_id": request.logical_call_id,
            "attempt": request.attempt,
        }
        self._publish(
            CapabilityStartedEvent(
                **event_fields,
                public_payload=CapabilityStartedPayload(
                    capability_name=request.capability_name,
                    input_summary=request.input,
                ),
            )
        )

        cache_key = (request.run_id, request.logical_call_id)
        definition = self.registry.get(request.capability_name)
        policy = _policy_from_definition(definition)
        if definition is None:
            result = self._failed(
                request,
                policy,
                "capability_not_registered",
                "能力未注册。",
            )
            self._publish_failed(result, event_fields, started)
            return result

        if request.caller not in definition.allowed_callers:
            result = self._failed(
                request,
                policy,
                "caller_not_allowed",
                "调用方无权执行该能力。",
            )
            self._publish_failed(result, event_fields, started)
            return result

        missing = [
            key for key in definition.required_input_keys if key not in request.input
        ]
        if missing:
            result = self._failed(
                request,
                policy,
                "invalid_input_schema",
                "能力输入缺少必填字段。",
            )
            self._publish_failed(result, event_fields, started)
            return result

        async with self._lock_for(cache_key):
            cached = self._results_by_logical_call_id.get(cache_key)
            if cached is not None:
                return self._reuse_or_conflict(
                    request,
                    cached,
                    cache_key,
                    event_fields,
                    started,
                )

            try:
                output = await asyncio.wait_for(
                    _invoke_handler(definition, request.input),
                    timeout=definition.timeout_ms / 1000,
                )
            except asyncio.TimeoutError:
                result = self._failed(
                    request,
                    policy,
                    "capability_timeout",
                    "能力执行超时。",
                )
                self._cache_result(cache_key, request, result)
                self._publish_failed(result, event_fields, started)
                return result
            except Exception:
                result = self._failed(
                    request,
                    policy,
                    "capability_handler_error",
                    "能力执行失败。",
                )
                self._cache_result(cache_key, request, result)
                self._publish_failed(result, event_fields, started)
                return result

            if not isinstance(output, dict):
                result = self._failed(
                    request,
                    policy,
                    "capability_output_schema_invalid",
                    "能力输出不是结构化对象。",
                )
                self._cache_result(cache_key, request, result)
                self._publish_failed(result, event_fields, started)
                return result

            missing_output = [
                key for key in definition.output_required_keys if key not in output
            ]
            if missing_output:
                result = self._failed(
                    request,
                    policy,
                    "capability_output_schema_invalid",
                    "能力输出缺少必填字段。",
                )
                self._cache_result(cache_key, request, result)
                self._publish_failed(result, event_fields, started)
                return result

            if definition.output_validator is not None:
                try:
                    definition.output_validator(output)
                except Exception:
                    result = self._failed(
                        request,
                        policy,
                        "capability_output_schema_invalid",
                        "能力输出结构不符合契约。",
                    )
                    self._cache_result(cache_key, request, result)
                    self._publish_failed(result, event_fields, started)
                    return result

            result = CapabilityResult(
                request_id=request.request_id,
                session_id=request.session_id,
                capability_name=request.capability_name,
                caller=request.caller,
                node_id=request.node_id,
                logical_call_id=request.logical_call_id,
                attempt=request.attempt,
                status=CapabilityStatus.SUCCESS,
                policy=policy,
                output=output,
            )
            self._cache_result(cache_key, request, result)
            self._publish_finished(result, event_fields, started)
            return result

    def _lock_for(self, cache_key: tuple[str, str]) -> asyncio.Lock:
        return self._locks_by_logical_call_id.setdefault(cache_key, asyncio.Lock())

    def _cache_result(
        self,
        cache_key: tuple[str, str],
        request: CapabilityRequest,
        result: CapabilityResult,
    ) -> None:
        self._results_by_logical_call_id[cache_key] = result
        self._request_signatures[cache_key] = (
            request.capability_name,
            request.caller,
            deepcopy(request.input),
        )

    def _reuse_or_conflict(
        self,
        request: CapabilityRequest,
        cached: CapabilityResult,
        cache_key: tuple[str, str],
        event_fields: dict,
        started: float,
    ) -> CapabilityResult:
        signature = self._request_signatures.get(cache_key)
        current_signature = (
            request.capability_name,
            request.caller,
            request.input,
        )
        if signature != current_signature:
            result = self._failed(
                request,
                cached.policy,
                "logical_call_conflict",
                "同一逻辑调用 ID 不允许改变能力、调用方或输入。",
            )
            self._publish_failed(result, event_fields, started)
            return result
        result = cached.model_copy(
            update={"attempt": request.attempt, "reused": True},
            deep=True,
        )
        if result.status is CapabilityStatus.FAILED:
            self._publish_failed(result, event_fields, started)
        else:
            self._publish_finished(result, event_fields, started)
        return result

    @staticmethod
    def _failed(
        request: CapabilityRequest,
        policy: CapabilityPolicy,
        code: str,
        message: str,
    ) -> CapabilityResult:
        return CapabilityResult(
            request_id=request.request_id,
            session_id=request.session_id,
            capability_name=request.capability_name,
            caller=request.caller,
            node_id=request.node_id,
            logical_call_id=request.logical_call_id,
            attempt=request.attempt,
            status=CapabilityStatus.FAILED,
            policy=policy,
            output={},
            error=CapabilityError(code=code, message=message),
        )

    def _publish_finished(
        self,
        result: CapabilityResult,
        event_fields: dict,
        started: float,
    ) -> None:
        self._publish(
            CapabilityFinishedEvent(
                **event_fields,
                public_payload=CapabilityFinishedPayload(
                    capability_name=result.capability_name,
                    status=result.status.value,
                    output_summary=result.output,
                    reused=result.reused,
                    latency_ms=int((perf_counter() - started) * 1000),
                ),
            )
        )

    def _publish_failed(
        self,
        result: CapabilityResult,
        event_fields: dict,
        started: float,
    ) -> None:
        self._publish(
            CapabilityFailedEvent(
                **event_fields,
                public_payload=CapabilityFailedPayload(
                    capability_name=result.capability_name,
                    error_code=result.error.code if result.error else "capability_failed",
                    fallback_used=True,
                    latency_ms=int((perf_counter() - started) * 1000),
                    error_message=result.error.message if result.error else None,
                ),
            )
        )

    def _publish(self, event) -> None:
        self.event_sink.publish(event)
        if self.trace_recorder is not None:
            self.trace_recorder.record(event.to_trace_event())


async def _invoke_handler(
    definition: CapabilityDefinition,
    payload: dict,
) -> dict:
    """在 async 边界内执行同步或异步能力 handler。"""

    if inspect.iscoroutinefunction(definition.handler):
        return await definition.handler(payload)
    output = await asyncio.to_thread(definition.handler, payload)
    if inspect.isawaitable(output):
        return await output
    return output


def _policy_from_definition(
    definition: CapabilityDefinition | None,
) -> CapabilityPolicy:
    if definition is None:
        return CapabilityPolicy(
            risk_level="unknown",
            timeout_ms=0,
            idempotency=CapabilityIdempotency.SIDE_EFFECTING,
        )
    if definition.risk_level == "read_only":
        idempotency = CapabilityIdempotency.READ_ONLY_REPEATABLE
    elif definition.risk_level == "calculation":
        idempotency = CapabilityIdempotency.DETERMINISTIC
    else:
        idempotency = CapabilityIdempotency.SIDE_EFFECTING
    return CapabilityPolicy(
        risk_level=definition.risk_level,
        timeout_ms=definition.timeout_ms,
        idempotency=idempotency,
    )
