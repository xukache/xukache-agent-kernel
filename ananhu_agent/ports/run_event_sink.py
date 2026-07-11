from __future__ import annotations

from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, Field, TypeAdapter

from ananhu_agent.schemas import TraceEvent, now_cn


class RunTransientPayload(BaseModel):
    """仅供当前进程展示的内容，禁止进入序列化和持久化投影。"""

    prompt: str | None = None
    message: str | None = None
    reasoning_content: str | None = None
    json_view: dict[str, Any] | list[Any] | None = None


class RunStartedPayload(BaseModel):
    runtime_name: str | None = None
    runtime_version: str | None = None


class NodeStartedPayload(BaseModel):
    phase: str
    input_summary: dict[str, Any] = Field(default_factory=dict)


class NodeFinishedPayload(BaseModel):
    phase: str
    latency_ms: int = Field(default=0, ge=0)
    patch_summary: dict[str, Any] = Field(default_factory=dict)


class NodeFailedPayload(BaseModel):
    phase: str
    error_code: str
    retryable: bool = False
    latency_ms: int = Field(default=0, ge=0)
    error_message: str | None = None


class ModelStartedPayload(BaseModel):
    profile: str
    prompt_ref: str
    input_summary: dict[str, Any] = Field(default_factory=dict)


class ModelFinishedPayload(BaseModel):
    profile: str
    provider: str
    model: str
    finish_reason: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    reasoning_available: bool = False
    reasoning_length: int = Field(default=0, ge=0)
    reasoning_original_chars: int = Field(default=0, ge=0)
    reasoning_truncated: bool = False
    latency_ms: int = Field(default=0, ge=0)


class ModelFailedPayload(BaseModel):
    profile: str
    provider: str | None = None
    error_code: str
    retryable: bool = False
    latency_ms: int = Field(default=0, ge=0)
    error_message: str | None = None
    status_code: int | None = None


class CapabilityStartedPayload(BaseModel):
    capability_name: str
    input_summary: dict[str, Any] = Field(default_factory=dict)


class CapabilityFinishedPayload(BaseModel):
    capability_name: str
    status: str
    output_summary: dict[str, Any] = Field(default_factory=dict)
    fallback_used: bool = False
    reused: bool = False
    latency_ms: int = Field(default=0, ge=0)


class CapabilityFailedPayload(BaseModel):
    capability_name: str
    error_code: str
    retryable: bool = False
    fallback_used: bool = False
    latency_ms: int = Field(default=0, ge=0)
    error_message: str | None = None


class RunCancelledPayload(BaseModel):
    reason: str = "user_cancelled"


class RunFinishedPayload(BaseModel):
    status: str
    stop_reason: str
    usage: dict[str, Any] | None = None
    final_state: dict[str, Any] | None = None
    latency_ms: int = Field(default=0, ge=0)


class RunEventBase(BaseModel):
    """框架中立运行事件基类，只允许显式公共投影进入业务 trace。"""

    run_id: str
    request_id: str
    session_id: str
    runtime_name: str | None = None
    runtime_version: str | None = None
    node_id: str | None = None
    logical_call_id: str | None = None
    attempt: int = Field(default=1, ge=1)
    sequence_no: int | None = Field(default=None, ge=1)
    transient_payload: RunTransientPayload | None = Field(default=None, exclude=True, repr=False)
    created_at: str = Field(default_factory=now_cn)

    def to_trace_event(self) -> TraceEvent:
        """通过受控字段构造持久化事件，绝不序列化 transient payload。"""
        latency_ms = getattr(self.public_payload, "latency_ms", None)
        return TraceEvent.new(
            run_id=self.run_id,
            request_id=self.request_id,
            session_id=self.session_id,
            event_type=self.kind,
            phase=self.node_id or "run",
            runtime_name=self.runtime_name,
            runtime_version=self.runtime_version,
            node_id=self.node_id,
            logical_call_id=self.logical_call_id,
            attempt=self.attempt,
            latency_ms=latency_ms,
            payload={
                "sequence_no": self.sequence_no,
                **self.public_payload.model_dump(mode="json"),
            },
        )


class RunStartedEvent(RunEventBase):
    kind: Literal["run_started"] = "run_started"
    public_payload: RunStartedPayload


class NodeStartedEvent(RunEventBase):
    kind: Literal["node_started"] = "node_started"
    public_payload: NodeStartedPayload


class NodeFinishedEvent(RunEventBase):
    kind: Literal["node_finished"] = "node_finished"
    public_payload: NodeFinishedPayload


class NodeFailedEvent(RunEventBase):
    kind: Literal["node_failed"] = "node_failed"
    public_payload: NodeFailedPayload


class ModelStartedEvent(RunEventBase):
    kind: Literal["model_started"] = "model_started"
    public_payload: ModelStartedPayload


class ModelFinishedEvent(RunEventBase):
    kind: Literal["model_finished"] = "model_finished"
    public_payload: ModelFinishedPayload


class ModelFailedEvent(RunEventBase):
    kind: Literal["model_failed"] = "model_failed"
    public_payload: ModelFailedPayload


class CapabilityStartedEvent(RunEventBase):
    kind: Literal["capability_started"] = "capability_started"
    public_payload: CapabilityStartedPayload


class CapabilityFinishedEvent(RunEventBase):
    kind: Literal["capability_finished"] = "capability_finished"
    public_payload: CapabilityFinishedPayload


class CapabilityFailedEvent(RunEventBase):
    kind: Literal["capability_failed"] = "capability_failed"
    public_payload: CapabilityFailedPayload


class RunCancelledEvent(RunEventBase):
    kind: Literal["run_cancelled"] = "run_cancelled"
    public_payload: RunCancelledPayload


class RunFinishedEvent(RunEventBase):
    kind: Literal["run_finished"] = "run_finished"
    public_payload: RunFinishedPayload


RunProgressEvent = Annotated[
    RunStartedEvent
    | NodeStartedEvent
    | NodeFinishedEvent
    | NodeFailedEvent
    | ModelStartedEvent
    | ModelFinishedEvent
    | ModelFailedEvent
    | CapabilityStartedEvent
    | CapabilityFinishedEvent
    | CapabilityFailedEvent
    | RunCancelledEvent
    | RunFinishedEvent,
    Field(discriminator="kind"),
]

RUN_PROGRESS_EVENT_ADAPTER = TypeAdapter(RunProgressEvent)


def validate_run_progress_event(event: RunProgressEvent) -> RunProgressEvent:
    """在所有 sink 边界应用同一个判别联合校验。"""
    return RUN_PROGRESS_EVENT_ADAPTER.validate_python(event)


class RunEventSink(Protocol):
    """运行时、模型和能力网关共享的同步发布端口。"""

    def publish(self, event: RunProgressEvent) -> None:
        """发布单个项目运行事件。"""

        ...


class NoOpRunEventSink:
    """非交互组合根使用的默认 sink。"""

    def publish(self, event: RunProgressEvent) -> None:
        validate_run_progress_event(event)
