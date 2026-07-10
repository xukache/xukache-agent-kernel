from __future__ import annotations

import asyncio
from threading import Lock

from ananhu_agent.ports.run_event_sink import (
    RunEventSink,
    RunProgressEvent,
    validate_run_progress_event,
)
from ananhu_agent.storage.runtime_stores import TraceRecorder


class TraceRecorderRunEventSink:
    """将实时事件显式投影为不含瞬态内容的业务 trace。"""

    def __init__(self, recorder: TraceRecorder) -> None:
        self.recorder = recorder

    def publish(self, event: RunProgressEvent) -> None:
        validated = validate_run_progress_event(event)
        self.recorder.record(validated.to_trace_event())


class QueueRunEventSink:
    """把已编号事件原样送入同一 event loop 的无界队列。"""

    def __init__(self, queue: asyncio.Queue[RunProgressEvent]) -> None:
        self.queue = queue

    def publish(self, event: RunProgressEvent) -> None:
        self.queue.put_nowait(validate_run_progress_event(event))


class CompositeRunEventSink:
    """按 run 原子编号，并严格按 trace、queue 顺序发布同一事件。"""

    def __init__(self, trace_sink: RunEventSink, queue_sink: RunEventSink) -> None:
        self.trace_sink = trace_sink
        self.queue_sink = queue_sink
        self._lock_registry_guard = Lock()
        self._run_locks: dict[str, Lock] = {}
        self._last_sequence_by_run: dict[str, int] = {}

    def publish(self, event: RunProgressEvent) -> None:
        validated = validate_run_progress_event(event)
        run_lock = self._lock_for(validated.run_id)
        with run_lock:
            next_sequence = self._last_sequence_by_run.get(validated.run_id, 0) + 1
            numbered = validated.model_copy(update={"sequence_no": next_sequence})
            self.trace_sink.publish(numbered)
            self.queue_sink.publish(numbered)
            self._last_sequence_by_run[validated.run_id] = next_sequence

    def _lock_for(self, run_id: str) -> Lock:
        with self._lock_registry_guard:
            return self._run_locks.setdefault(run_id, Lock())
