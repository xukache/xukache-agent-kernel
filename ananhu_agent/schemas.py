from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

CN_TZ = timezone(timedelta(hours=8))


def now_cn() -> str:
    """返回适合 trace 记录的中国时区时间戳。"""
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


class RequestContext(BaseModel):
    """单轮 CLI 请求的不可变输入信封。

    这是后续 Agent 消息、工具调用、trace 事件、任务状态和运行报告的根关联对象。
    """

    request_id: str
    session_id: str
    turn_id: int
    user_query: str
    input_type: Literal["text"] = "text"
    province: str | None = None
    city: str | None = None
    created_at: str

    @classmethod
    def new(
        cls,
        session_id: str,
        turn_id: int,
        user_query: str,
        province: str | None = None,
        city: str | None = None,
    ) -> RequestContext:
        """创建带有关联 ID 和中国时区时间戳的请求上下文。"""
        return cls(
            request_id=f"req_{uuid4().hex[:12]}",
            session_id=session_id,
            turn_id=turn_id,
            user_query=user_query,
            province=province,
            city=city,
            created_at=now_cn(),
        )


class ConversationState(BaseModel):
    """由编排器持有、Agent 只读的会话记忆。"""

    history_summary: str = ""
    last_user_intent: str | None = None
    last_answer_summary: str = ""
    active_slots: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    """跨轮会话记忆快照。

    该结构只由 AgentOrchestrator 读写，用于在 CLI 多轮交互中恢复轻量上下文。
    """

    session_id: str
    turn_id: int
    history_summary: str = ""
    last_user_intent: str | None = None
    last_answer_summary: str = ""
    active_slots: dict[str, Any] = Field(default_factory=dict)
    updated_at: str


class IntentResult(BaseModel):
    """路由规划前的意图识别结构化结果。"""

    intent: str
    confidence: float
    slots: dict[str, Any] = Field(default_factory=dict)
    is_composite: bool = False
    missing_slots: list[str] = Field(default_factory=list)
    ask_clarification: str | None = None


class AgentPlan(BaseModel):
    """编排器为当前轮生成的 Agent 路由决策。"""

    route_agents: list[str]
    required_tools: list[str] = Field(default_factory=list)
    execution_mode: Literal["sync_serial"] = "sync_serial"


class ToolCallRequest(BaseModel):
    """Agent 发出的工具调用请求。

    Agent 只能请求工具，实际执行必须经过 ToolExecutor，以集中处理权限、校验、fallback 和 trace。
    """

    tool_call_id: str
    tool_name: str
    called_by: str
    input: dict[str, Any]


class ToolCallResult(BaseModel):
    """ToolExecutor 完成一次工具尝试后返回的归一化结果。"""

    tool_call_id: str
    tool_name: str
    called_by: str
    tool_status: Literal["success", "failed"]
    tool_error_code: str | None
    latency_ms: int
    input: dict[str, Any]
    output: dict[str, Any]
    fallback_used: bool = False
    fallback_reason: str | None = None


class AgentMessage(BaseModel):
    """MVP Agent 返回的单条结构化消息。

    编排器消费这些消息，用于合并槽位、执行工具请求、聚合草稿答案和判断是否需要追问。
    """

    agent_name: str
    status: Literal["success", "failed", "need_clarification"]
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """安全检查和最终回复前的输出校验结果。"""

    passed: bool
    issues: list[str] = Field(default_factory=list)


class SafetyResult(BaseModel):
    """最终答案候选内容的政务安全守卫结果。"""

    passed: bool
    warnings: list[str] = Field(default_factory=list)


class TaskState(BaseModel):
    """当前轮运行快照，用于恢复、诊断和 badcase 分流。"""

    id: str
    session_id: str
    turn_id: int
    user_query: str
    status: str
    current_phase: str
    raw_intent: str | None = None
    revised_intent: str | None = None
    active_slots: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    route_agents: list[str] = Field(default_factory=list)
    prompt_refs: list[str] = Field(default_factory=list)
    tool_steps: list[str] = Field(default_factory=list)
    model_attempts: int = 0
    fallback_used: bool = False
    error_message: str | None = None


class RunReport(BaseModel):
    """单轮运行结束摘要，用于指标统计、eval 和运行复盘。"""

    id: str
    session_id: str
    final_status: str
    final_intent: str | None
    route_agents: list[str]
    tool_count: int
    model_attempts: int
    prompt_refs: list[str]
    prompt_metadata: dict[str, Any]
    output_schema_valid_rate: float
    token_usage: dict[str, Any]
    latency_ms: int
    fallback_used: bool
    safety_result: dict[str, Any]
    badcase_candidate: bool


class BadcaseRecord(BaseModel):
    """用户主动反馈或系统规则沉淀的 badcase 记录。"""

    id: str
    request_id: str
    session_id: str
    turn_id: int
    query: str
    predicted_intent: str | None = None
    issue_type: str
    agent_route: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    actual_answer: str
    expected_answer: str = ""
    correction_note: str = ""
    added_to_eval: bool = False
    fixed: bool = False
    created_at: str


class AgentContext(BaseModel):
    """传入无状态 Agent 的完整单轮上下文。

    只有 AgentOrchestrator 可以变更或替换该对象；Agent 只读取上下文并返回 AgentMessage，
    不直接写入任务状态。
    """

    request: RequestContext
    conversation: ConversationState = Field(default_factory=ConversationState)
    intent_result: IntentResult | None = None
    agent_plan: AgentPlan | None = None
    tool_results: list[ToolCallResult] = Field(default_factory=list)
    agent_outputs: list[AgentMessage] = Field(default_factory=list)
    draft_final_answer: str | None = None
    verification_result: VerificationResult | None = None
    safety_result: SafetyResult | None = None
    final_answer: str | None = None

    @classmethod
    def new_for_query(
        cls,
        session_id: str,
        turn_id: int,
        user_query: str,
        province: str | None = None,
        city: str | None = None,
    ) -> AgentContext:
        """构建启动单轮 CLI 咨询所需的最小上下文。"""
        return cls(
            request=RequestContext.new(
                session_id=session_id,
                turn_id=turn_id,
                user_query=user_query,
                province=province,
                city=city,
            )
        )


class TraceEvent(BaseModel):
    """单个请求运行时间线中的追加式事件。"""

    id: str
    request_id: str
    session_id: str
    event_type: str
    phase: str
    payload: dict[str, Any]
    latency_ms: int | None = None
    created_at: str

    @classmethod
    def new(
        cls,
        request_id: str,
        session_id: str,
        event_type: str,
        phase: str,
        payload: dict[str, Any],
        latency_ms: int | None = None,
    ) -> TraceEvent:
        """创建带有事件 ID 和标准时间戳的 trace 事件。"""
        return cls(
            id=f"trace_{uuid4().hex[:12]}",
            request_id=request_id,
            session_id=session_id,
            event_type=event_type,
            phase=phase,
            payload=payload,
            latency_ms=latency_ms,
            created_at=now_cn(),
        )
