from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.ports.run_event_sink import RunProgressEvent
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.workflow.contracts import RunRequest


class CollectingRunEventSink:
    def __init__(self) -> None:
        self.events: list[RunProgressEvent] = []

    def publish(self, event: RunProgressEvent) -> None:
        self.events.append(event)


def _request(run_id: str = "run_contract") -> RunRequest:
    return RunRequest(
        run_id=run_id,
        request_id="req_contract",
        session_id="sess_contract",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
        created_at="2026-07-10T00:00:00+08:00",
    )


def _run_with_events(tmp_path, runtime_name: str) -> list[RunProgressEvent]:
    sink = CollectingRunEventSink()
    runtime = create_default_runtime(
        tmp_path / runtime_name,
        RuntimeSettings(runtime_dir=tmp_path / runtime_name, runtime=runtime_name),
        event_sink=sink,
    )
    asyncio.run(runtime.invoke(_request()))
    return sink.events


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_each_node_has_one_terminal_event_and_run_finished_is_last(tmp_path, runtime_name):
    events = _run_with_events(tmp_path, runtime_name)

    for started in [event for event in events if event.kind == "node_started"]:
        terminals = [
            event
            for event in events
            if event.node_id == started.node_id
            and event.kind in {"node_finished", "node_failed"}
        ]
        assert len(terminals) == 1
    assert events[-1].kind == "run_finished"
    assert sum(event.kind == "run_finished" for event in events) == 1


def test_cancelled_run_has_one_cancel_and_one_terminal_barrier(tmp_path):
    sink = CollectingRunEventSink()
    runtime = create_default_runtime(
        tmp_path,
        RuntimeSettings(runtime_dir=tmp_path, runtime="native"),
        event_sink=sink,
    )

    async def cancel_blocked_runtime() -> None:
        blocked = asyncio.Event()

        class BlockingModelGateway:
            async def generate_structured(self, request):
                blocked.set()
                await asyncio.Event().wait()

        runtime.intent_agent.model_gateway = BlockingModelGateway()
        task = asyncio.create_task(runtime.invoke(_request("run_cancelled")))
        await blocked.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_blocked_runtime())

    assert [event.kind for event in sink.events[-2:]] == ["run_cancelled", "run_finished"]
    assert sum(event.kind == "run_cancelled" for event in sink.events) == 1
    assert sum(event.kind == "run_finished" for event in sink.events) == 1
    assert sink.events[-1].public_payload.status == "cancelled"
    assert sink.events[-1].public_payload.stop_reason == "user_cancelled"


def test_capability_events_keep_full_run_identity(tmp_path):
    events = _run_with_events(tmp_path, "native")
    event = next(event for event in events if event.kind == "capability_started")

    assert (event.run_id, event.request_id, event.logical_call_id) == (
        "run_contract",
        "req_contract",
        "req_contract:payment-calculation",
    )


def test_event_payloads_never_contain_framework_or_ui_types(tmp_path):
    for event in _run_with_events(tmp_path, "langgraph"):
        assert not _recursively_contains_module(
            event.model_dump(),
            ("langgraph", "textual", "rich"),
        )


def test_native_and_langgraph_emit_equivalent_progress_events(tmp_path):
    native = _normalize_progress(_run_with_events(tmp_path, "native"))
    langgraph = _normalize_progress(_run_with_events(tmp_path, "langgraph"))

    assert native == langgraph


def _recursively_contains_module(value: Any, modules: tuple[str, ...]) -> bool:
    value_module = type(value).__module__.lower()
    if any(module in value_module for module in modules):
        return True
    if isinstance(value, dict):
        return any(
            _recursively_contains_module(key, modules)
            or _recursively_contains_module(item, modules)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_recursively_contains_module(item, modules) for item in value)
    return False


def _normalize_progress(events: list[RunProgressEvent]) -> list[dict[str, Any]]:
    normalized = []
    for event in events:
        payload = event.public_payload.model_dump()
        payload.pop("runtime_name", None)
        payload.pop("runtime_version", None)
        payload.pop("latency_ms", None)
        normalized.append(
            {
                "kind": event.kind,
                "run_id": event.run_id,
                "request_id": event.request_id,
                "session_id": event.session_id,
                "node_id": event.node_id,
                "logical_call_id": event.logical_call_id,
                "attempt": event.attempt,
                "payload": payload,
            }
        )
    return normalized
