import asyncio

from ananhu_agent.cli.tui.presentation import RunEventReducer
from ananhu_agent.infrastructure.events.run_event_sinks import (
    CompositeRunEventSink,
    QueueRunEventSink,
    TraceRecorderRunEventSink,
)
from ananhu_agent.ports.run_event_sink import (
    ModelFinishedEvent,
    ModelFinishedPayload,
    NodeFinishedEvent,
    NodeFinishedPayload,
    NodeStartedEvent,
    NodeStartedPayload,
    RunFinishedEvent,
    RunFinishedPayload,
    RunTransientPayload,
)
from ananhu_agent.storage.runtime_stores import TraceRecorder


def _event_fields(run_id: str = "run_1") -> dict[str, str]:
    return {
        "run_id": run_id,
        "request_id": f"req_{run_id}",
        "session_id": "sess_1",
    }


def _node_started(run_id: str = "run_1", sequence_no: int | None = None) -> NodeStartedEvent:
    return NodeStartedEvent(
        **_event_fields(run_id),
        node_id="understand",
        sequence_no=sequence_no,
        public_payload=NodeStartedPayload(phase="understand"),
    )


def _node_finished(run_id: str = "run_1", sequence_no: int | None = None) -> NodeFinishedEvent:
    return NodeFinishedEvent(
        **_event_fields(run_id),
        node_id="understand",
        sequence_no=sequence_no,
        public_payload=NodeFinishedPayload(phase="understand", latency_ms=5),
    )


def _run_finished(run_id: str = "run_1", sequence_no: int | None = None) -> RunFinishedEvent:
    return RunFinishedEvent(
        **_event_fields(run_id),
        sequence_no=sequence_no,
        public_payload=RunFinishedPayload(status="completed", stop_reason="completed", latency_ms=8),
    )


def test_composite_sink_assigns_monotonic_sequence_and_projects_trace(tmp_path):
    queue: asyncio.Queue[object] = asyncio.Queue()
    recorder = TraceRecorder(tmp_path / "traces.jsonl")
    sink = CompositeRunEventSink(
        TraceRecorderRunEventSink(recorder),
        QueueRunEventSink(queue),
    )

    sink.publish(_node_started())
    sink.publish(_node_finished())

    first, second = queue.get_nowait(), queue.get_nowait()
    assert [first.sequence_no, second.sequence_no] == [1, 2]
    rows = recorder.read_all()
    assert [row["event_type"] for row in rows] == ["node_started", "node_finished"]
    assert [row["payload"]["sequence_no"] for row in rows] == [1, 2]


def test_transient_payload_never_enters_trace_projection():
    event = ModelFinishedEvent(
        **_event_fields(),
        node_id="understand",
        logical_call_id="model_1",
        public_payload=ModelFinishedPayload(
            profile="intent_fast",
            provider="fake",
            model="fake-intent",
            reasoning_available=True,
            reasoning_length=16,
        ),
        transient_payload=RunTransientPayload(reasoning_content="CANARY_REASONING"),
    )

    assert "CANARY_REASONING" not in event.model_dump_json()
    assert "CANARY_REASONING" not in event.to_trace_event().model_dump_json()


def test_consumer_rejects_sequence_gap_without_permanent_spinner():
    inspector = RunEventReducer()
    inspector.apply(_node_started(sequence_no=1))
    inspector.apply(_node_finished(sequence_no=3))
    inspector.apply(_node_finished(sequence_no=2))
    inspector.apply(_run_finished(sequence_no=4))

    state = inspector.state_for("run_1")
    assert state.error_code == "event_sequence_gap"
    assert state.running is False
    assert state.applied_sequences == [1]
    assert state.terminal_barrier_seen is True


def test_duplicate_and_interleaved_runs_are_isolated():
    inspector = RunEventReducer()
    for event in [
        _node_started("run_a", 1),
        _node_started("run_b", 1),
        _node_started("run_a", 1),
        _node_finished("run_a", 2),
    ]:
        inspector.apply(event)

    assert inspector.state_for("run_a").applied_sequences == [1, 2]
    assert inspector.state_for("run_b").applied_sequences == [1]
