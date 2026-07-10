from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ananhu_agent.ports.model_gateway import ModelResult
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


@dataclass(frozen=True)
class UsageDetail:
    """单次模型结果的展示明细，不作为计费事实源。"""

    provider: str
    model: str
    usage_source: str
    reported: bool
    input_tokens: int
    output_tokens: int
    cache_tokens: int
    total_tokens: int
    latency_ms: int
    inconsistent: bool = False


@dataclass(frozen=True)
class UsageSummary:
    """本轮模型 usage 的 TUI 展示聚合。"""

    calls: int
    reported: bool
    usage_source: str
    input_tokens: int
    output_tokens: int
    cache_tokens: int
    total_tokens: int
    latency_ms: int
    details: list[UsageDetail]
    inconsistent: bool = False


def aggregate_usage(results: Iterable[ModelResult]) -> UsageSummary:
    details: list[UsageDetail] = []
    for result in results:
        usage = result.usage
        expected_total = usage.input_tokens + usage.output_tokens
        inconsistent = usage.reported and usage.total_tokens != expected_total
        details.append(UsageDetail(
            provider=result.provider,
            model=result.model,
            usage_source=usage.usage_source,
            reported=usage.reported,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_tokens=usage.cache_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=result.latency_ms,
            inconsistent=inconsistent,
        ))

    reported = bool(details) and all(detail.reported for detail in details)
    sources = {detail.usage_source for detail in details}
    return UsageSummary(
        calls=len(details),
        reported=reported,
        usage_source=next(iter(sources)) if len(sources) == 1 else "mixed",
        input_tokens=sum(detail.input_tokens for detail in details),
        output_tokens=sum(detail.output_tokens for detail in details),
        cache_tokens=sum(detail.cache_tokens for detail in details),
        total_tokens=sum(detail.total_tokens for detail in details),
        latency_ms=sum(detail.latency_ms for detail in details),
        details=details,
        inconsistent=any(detail.inconsistent for detail in details),
    )


def format_usage_line(results: Iterable[ModelResult] | UsageSummary, elapsed_ms: int) -> str:
    """把本轮模型 usage 格式化为单行状态文本。"""

    summary = results if isinstance(results, UsageSummary) else aggregate_usage(results)
    if summary.calls == 0:
        return "model · 0 calls · tokens unknown · ⚡ --"

    if summary.usage_source == "fake":
        return "fake · 0 tokens · ⚡ --"

    detail_suffix = _detail_suffix(summary)
    inconsistent_suffix = " · inconsistent" if summary.inconsistent else ""
    if not summary.reported:
        return f"{summary.calls} calls · tokens unknown · ⚡ --{detail_suffix}{inconsistent_suffix}"

    latency_ms = summary.latency_ms or elapsed_ms
    speed = summary.output_tokens / (latency_ms / 1000) if latency_ms > 0 else 0
    return (
        f"{summary.calls} calls · Σ {summary.total_tokens} tokens · "
        f"⚡ {speed:.1f} tok/s{detail_suffix}{inconsistent_suffix}"
    )


def _detail_suffix(summary: UsageSummary) -> str:
    cache_tokens = sum(detail.cache_tokens for detail in summary.details)
    if cache_tokens <= 0:
        return ""
    return f" · cache {cache_tokens}"
