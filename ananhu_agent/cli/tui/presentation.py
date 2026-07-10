from __future__ import annotations

from dataclasses import dataclass, field

from ananhu_agent.ports.run_event_sink import RunProgressEvent, validate_run_progress_event


@dataclass
class RunEventViewState:
    """单个 run 的纯展示状态，不参与业务状态或恢复。"""

    run_id: str
    running: bool = True
    error_code: str | None = None
    applied_sequences: list[int] = field(default_factory=list)
    terminal_barrier_seen: bool = False


class RunEventReducer:
    """隔离各 run，并把重复、gap 和终止屏障收敛为确定展示状态。"""

    def __init__(self) -> None:
        self._states: dict[str, RunEventViewState] = {}

    def apply(self, event: RunProgressEvent) -> None:
        validated = validate_run_progress_event(event)
        state = self._states.setdefault(
            validated.run_id,
            RunEventViewState(run_id=validated.run_id),
        )

        if state.error_code == "event_sequence_gap":
            if validated.kind == "run_finished":
                state.terminal_barrier_seen = True
                state.running = False
            return

        sequence_no = validated.sequence_no
        expected = (state.applied_sequences[-1] if state.applied_sequences else 0) + 1
        if sequence_no is None:
            state.error_code = "event_sequence_missing"
            state.running = False
            return
        if sequence_no < expected:
            return
        if sequence_no > expected:
            state.error_code = "event_sequence_gap"
            state.running = False
            return

        state.applied_sequences.append(sequence_no)
        if validated.kind == "run_finished":
            state.terminal_barrier_seen = True
            state.running = False

    def state_for(self, run_id: str) -> RunEventViewState:
        return self._states[run_id]
