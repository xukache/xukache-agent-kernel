from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, SecretStr

from ananhu_agent.ports.model_gateway import ModelResult
from ananhu_agent.ports.run_event_sink import RunProgressEvent, validate_run_progress_event
from ananhu_agent.workflow.contracts import StopReason, WorkflowResult


def visible_result_message(result: WorkflowResult) -> str:
    """将框架中立结果投影为 CLI 与 TUI 都可直接展示的非空文本。"""

    if result.final_answer:
        return result.final_answer
    if result.clarification_question:
        return result.clarification_question
    if result.error_message:
        return result.error_message

    messages = {
        StopReason.INSUFFICIENT_EVIDENCE: "暂未检索到足以支持结论的政策依据，请补充地区或具体工伤情形后再试。",
        StopReason.CAPABILITY_FAILED: "相关能力暂时不可用，请稍后重试或补充信息。",
        StopReason.SAFETY_BLOCKED: "为避免造成误导，暂不能给出该回复，请补充具体情况。",
        StopReason.USER_CANCELLED: "本次咨询已取消。",
    }
    return messages.get(result.stop_reason, "系统暂时无法生成有效回复，请稍后重试。")


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


_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|authorization|cookie|token|password|passwd|secret|"
    r"proxy|credential|access[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class JsonView:
    """受控 JSON 文本及裁剪元数据，供展示层渲染而不承担持久化职责。"""

    text: str
    original_chars: int
    truncated: bool


def sanitize(value: Any, *, configured_secrets: Iterable[str] = ()) -> Any:
    """递归隐藏瞬态展示中的凭据，同时保留非敏感诊断字段。"""

    secrets = tuple(secret for secret in configured_secrets if secret)
    return _sanitize_value(value, secrets)


def _sanitize_value(value: Any, configured_secrets: tuple[str, ...]) -> Any:
    if isinstance(value, SecretStr):
        return "***"
    if isinstance(value, BaseModel):
        return _sanitize_value(value.model_dump(), configured_secrets)
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            clean[key_text] = "***" if _is_sensitive_key(key_text) else _sanitize_value(
                item,
                configured_secrets,
            )
        return clean
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_sanitize_value(item, configured_secrets) for item in value]
    if isinstance(value, str):
        clean = value
        for secret in configured_secrets:
            clean = clean.replace(secret, "***")
        return _sanitize_url(clean)
    if isinstance(value, Exception):
        return f"{type(value).__name__}: {_sanitize_value(str(value), configured_secrets)}"
    return value


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY.search(key))


def _sanitize_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc or not parsed.query:
        if not parsed.scheme or not parsed.netloc or parsed.username is None:
            return value
    netloc = parsed.netloc
    if parsed.username is not None or parsed.password is not None:
        netloc = f"***@{parsed.netloc.rsplit('@', maxsplit=1)[-1]}"
    query = [
        (key, "***" if _is_sensitive_key(key) else item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunsplit((
        parsed.scheme,
        netloc,
        parsed.path,
        urlencode(query),
        parsed.fragment,
    ))


def json_view(value: Any, *, max_chars: int = 2_000, configured_secrets: Iterable[str] = ()) -> JsonView:
    """生成安全 JSON 预览；超长内容只保留前缀与原始长度。"""

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    text = json.dumps(
        sanitize(value, configured_secrets=configured_secrets),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    )
    original_chars = len(text)
    if original_chars <= max_chars:
        return JsonView(text=text, original_chars=original_chars, truncated=False)
    return JsonView(
        text=f"{text[:max_chars]}\n... [truncated; original_chars={original_chars}]",
        original_chars=original_chars,
        truncated=True,
    )


@dataclass
class InspectorItem:
    """检查器中一个独立可展开项目，状态仅属于当前轮展示。"""

    item_id: str
    label: str
    kind: str
    value: Any = field(default_factory=dict)
    parent_id: str | None = None
    expanded: bool = False
    user_toggled: bool = False
    show_raw_json: bool = False
    children: list[str] = field(default_factory=list)

    @property
    def preview(self) -> JsonView:
        return json_view(self.value, max_chars=600)


class InspectorModel:
    """把项目实时事件投影为框架无关的检查器树模型。"""

    def __init__(self, *, configured_secrets: Iterable[str] = ()) -> None:
        self._items: dict[str, InspectorItem] = {}
        self.roots: list[str] = []
        self._configured_secrets = tuple(secret for secret in configured_secrets if secret)

    def item(self, item_id: str) -> InspectorItem:
        return self._items[item_id]

    def items(self) -> list[InspectorItem]:
        return list(self._items.values())

    def toggle(self, item_id: str) -> None:
        item = self.item(item_id)
        item.expanded = not item.expanded
        item.user_toggled = True

    def toggle_from_mouse(self, item_id: str) -> None:
        self.toggle(item_id)

    def toggle_from_keyboard(self, item_id: str) -> None:
        self.toggle(item_id)

    def toggle_raw_json(self, item_id: str) -> None:
        item = self.item(item_id)
        item.show_raw_json = not item.show_raw_json

    def ensure(
        self,
        item_id: str,
        *,
        label: str,
        kind: str,
        value: Any = None,
        parent_id: str | None = None,
    ) -> InspectorItem:
        item = self._items.get(item_id)
        if item is None:
            item = InspectorItem(
                item_id=item_id,
                label=label,
                kind=kind,
                value=sanitize(
                    value if value is not None else {},
                    configured_secrets=self._configured_secrets,
                ),
                parent_id=parent_id,
            )
            self._items[item_id] = item
            if parent_id is None:
                self.roots.append(item_id)
            else:
                parent = self._items[parent_id]
                parent.children.append(item_id)
        elif value is not None:
            item.value = sanitize(value, configured_secrets=self._configured_secrets)
        return item


def inspector_model(
    events: Iterable[RunProgressEvent],
    *,
    configured_secrets: Iterable[str] = (),
) -> InspectorModel:
    """以事件顺序构建单轮树，展示层不读取 Runtime 或框架内部状态。"""

    model = InspectorModel(configured_secrets=configured_secrets)
    for event in events:
        event = validate_run_progress_event(event)
        if event.kind.startswith("node_"):
            _add_node_event(model, event)
        elif event.kind.startswith("model_"):
            _add_model_event(model, event)
        elif event.kind.startswith("capability_"):
            _add_capability_event(model, event)
    return model


def _node_item(model: InspectorModel, node_id: str | None) -> InspectorItem:
    resolved_id = node_id or "run"
    return model.ensure(
        resolved_id,
        label=resolved_id,
        kind="node",
        value={},
    )


def _add_node_event(model: InspectorModel, event: RunProgressEvent) -> None:
    node = _node_item(model, event.node_id)
    if event.kind == "node_started":
        node.expanded = True
        model.ensure(
            f"{node.item_id}.input",
            label="节点输入",
            kind="input",
            value=event.public_payload.input_summary,
            parent_id=node.item_id,
        )
    elif event.kind == "node_finished":
        if not node.user_toggled:
            node.expanded = False
        model.ensure(
            f"{node.item_id}.output",
            label="节点输出",
            kind="output",
            value=event.public_payload.patch_summary,
            parent_id=node.item_id,
        )
    elif event.kind == "node_failed":
        node.expanded = True
        model.ensure(
            f"{node.item_id}.error",
            label="节点错误",
            kind="error",
            value={
                "error_code": event.public_payload.error_code,
                "message": event.public_payload.error_message,
            },
            parent_id=node.item_id,
        )


def _add_model_event(model: InspectorModel, event: RunProgressEvent) -> None:
    node = _node_item(model, event.node_id)
    call_id = event.logical_call_id or str(event.sequence_no or "unknown")
    model_item_id = f"{node.item_id}.model.{call_id}"
    model_item = model.ensure(
        model_item_id,
        label="模型调用",
        kind="model",
        value={},
        parent_id=node.item_id,
    )
    if event.kind == "model_started":
        model.ensure(
            f"{model_item_id}.input",
            label="模型输入",
            kind="input",
            value=event.public_payload.input_summary,
            parent_id=model_item_id,
        )
    elif event.kind == "model_finished":
        model.ensure(
            f"{model_item_id}.output",
            label="模型输出",
            kind="output",
            value=event.public_payload.output_summary,
            parent_id=model_item_id,
        )
        reasoning = event.transient_payload.reasoning_content if event.transient_payload else None
        if reasoning:
            model.ensure(
                f"{model_item_id}.reasoning",
                label="模型思考",
                kind="reasoning",
                value={"content": reasoning},
                parent_id=model_item_id,
            )
    elif event.kind == "model_failed":
        model_item.expanded = True
        model.ensure(
            f"{model_item_id}.error",
            label="模型错误",
            kind="error",
            value={
                "error_code": event.public_payload.error_code,
                "message": event.public_payload.error_message,
            },
            parent_id=model_item_id,
        )


def _add_capability_event(model: InspectorModel, event: RunProgressEvent) -> None:
    node = _node_item(model, event.node_id)
    payload = event.public_payload
    name = payload.capability_name
    call_id = event.logical_call_id or str(event.sequence_no or "unknown")
    capability_id = f"{node.item_id}.tool.{name}.{call_id}"
    capability = model.ensure(
        capability_id,
        label=name,
        kind="tool",
        value={},
        parent_id=node.item_id,
    )
    if event.kind == "capability_started":
        model.ensure(
            f"{capability_id}.input",
            label="工具输入",
            kind="input",
            value=payload.input_summary,
            parent_id=capability_id,
        )
    elif event.kind == "capability_finished":
        model.ensure(
            f"{capability_id}.output",
            label="工具输出",
            kind="output",
            value=payload.output_summary,
            parent_id=capability_id,
        )
    elif event.kind == "capability_failed":
        capability.expanded = True
        model.ensure(
            f"{capability_id}.error",
            label="工具错误",
            kind="error",
            value={"error_code": payload.error_code, "message": payload.error_message},
            parent_id=capability_id,
        )
