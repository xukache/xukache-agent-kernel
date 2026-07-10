from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from ananhu_agent.schemas import AgentContext, now_cn

# 工作流协议版本；持久化、回放和后续迁移都以它判断状态结构兼容性。
SCHEMA_VERSION = "workflow.v1"


class WorkflowPhase(str, Enum):
    """业务状态机的稳定阶段，禁止绑定具体运行时框架节点类型。"""

    UNDERSTAND = "understand"
    MERGE_FACTS = "merge_facts"
    VALIDATE_FACTS = "validate_facts"
    CLARIFY = "clarify"
    RESOLVE_JURISDICTION = "resolve_jurisdiction"
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE_EVIDENCE = "validate_evidence"
    COMPOSE = "compose"
    SAFETY = "safety"
    COMPLETE = "complete"


class RunStatus(str, Enum):
    """单次 run 的框架中立状态。"""

    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class StopReason(str, Enum):
    """运行终止原因，供 Native 和后续 LangGraph Runtime 共同遵守。"""

    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CAPABILITY_FAILED = "capability_failed"
    SAFETY_BLOCKED = "safety_blocked"


class RunRequest(BaseModel):
    """单次工作流运行的不可变输入信封。

    request_id 关联用户请求，run_id 关联一次运行尝试，session_id 关联多轮会话，
    case_id 关联跨会话案件事实，message_id 关联外部消息或 CLI turn。
    """

    schema_version: Literal["workflow.v1"] = Field(
        default=SCHEMA_VERSION,
        description="请求协议版本，用于判断持久化数据能否安全读取。",
    )
    run_id: str = Field(description="单次工作流运行 ID；重试或恢复时不得冒充 request_id。")
    request_id: str = Field(description="用户一次请求的根关联 ID，沿用旧 RequestContext。")
    session_id: str = Field(description="多轮会话 ID，用于关联 SessionState 和对话记忆。")
    case_id: str | None = Field(
        default=None,
        description="跨会话案件事实 ID；当前 CLI MVP 尚未持久化 CaseRecord。",
    )
    message_id: str | None = Field(
        default=None,
        description="外部消息或 CLI turn 的 ID；当前可为空，供后续外部入口对齐。",
    )
    turn_id: int = Field(description="会话内轮次，来自旧 RequestContext.turn_id。")
    user_query: str = Field(description="当前用户原始问题，后续上下文裁剪不得丢弃。")
    input_type: Literal["text"] = Field(default="text", description="当前 MVP 只支持文本输入。")
    trusted_jurisdiction: dict[str, str | None] = Field(
        default_factory=dict,
        description="由编排器确认后的可信地区，不让 Agent 自行决定政策适用边界。",
    )
    created_at: str = Field(description="请求创建时间，沿用中国时区 trace 时间格式。")

    @classmethod
    def from_agent_context(
        cls,
        ctx: AgentContext,
        run_id: str | None = None,
        case_id: str | None = None,
        message_id: str | None = None,
    ) -> RunRequest:
        """从旧 AgentContext 显式构造新请求协议，不改变现有运行行为。

        参数:
            ctx: 当前 Native MVP 使用的共享上下文，只读提取请求身份和地区。
            run_id: 调用方指定的运行 ID；为空时生成新的 `run_` 前缀 ID。
            case_id: 案件事实 ID；任务 26 只预留关联位，不创建 CaseRecord。
            message_id: 外部消息 ID；当前 CLI 可不传。

        返回:
            框架中立 `RunRequest`，供 `WorkflowState` 和未来 Runtime 使用。
        """

        # 可信 jurisdiction 只能来自编排器已同步到 RequestContext 的地区字段。
        jurisdiction = {
            key: value
            for key, value in {
                "province": ctx.request.province,
                "city": ctx.request.city,
            }.items()
            if value is not None
        }
        return cls(
            run_id=run_id or f"run_{uuid4().hex[:12]}",
            request_id=ctx.request.request_id,
            session_id=ctx.request.session_id,
            case_id=case_id,
            message_id=message_id,
            turn_id=ctx.request.turn_id,
            user_query=ctx.request.user_query,
            input_type=ctx.request.input_type,
            trusted_jurisdiction=jurisdiction,
            created_at=ctx.request.created_at,
        )


class WorkflowState(BaseModel):
    """单次 run 的可序列化业务状态投影。

    任务 26 只定义状态形状和旧协议映射；状态增量和 reducer 在任务 27 冻结。
    """

    schema_version: Literal["workflow.v1"] = Field(
        default=SCHEMA_VERSION,
        description="状态协议版本；reducer 和 checkpointer 必须按版本处理。",
    )
    run_id: str = Field(description="单次工作流运行 ID，与 RunRequest.run_id 保持一致。")
    request_id: str = Field(description="用户请求 ID，用于关联 trace、badcase 和报告。")
    session_id: str = Field(description="会话 ID，用于关联多轮记忆。")
    case_id: str | None = Field(default=None, description="案件事实 ID，任务 26 只做关联预留。")
    message_id: str | None = Field(default=None, description="外部消息 ID，当前 CLI 可为空。")
    phase: WorkflowPhase = Field(
        default=WorkflowPhase.UNDERSTAND,
        description="当前业务阶段，后续 Runtime 按它做条件路由和终止判断。",
    )
    status: RunStatus = Field(default=RunStatus.RUNNING, description="当前 run 的总体状态。")
    stop_reason: StopReason | None = Field(
        default=None,
        description="停止或失败原因；RUNNING 状态下为空。",
    )
    attempt_count: int = Field(
        default=0,
        description="运行级尝试次数；任务 27 会进一步区分 node/capability attempt。",
    )
    capability_call_count: int = Field(default=0, description="本次 run 已执行的能力调用数量。")
    applied_patch_ids: list[str] = Field(
        default_factory=list,
        description="已经应用过的 StatePatch ID，用于重放和节点重试时去重。",
    )
    case_facts: dict[str, Any] = Field(
        default_factory=dict,
        description="已确认或当前轮提取的案件事实投影，当前来自 active_slots。",
    )
    intent_result: dict[str, Any] | None = Field(default=None, description="意图识别结构化结果。")
    execution_plan: dict[str, Any] | None = Field(default=None, description="Agent 路由和工具计划。")
    capability_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="能力执行结果；当前映射旧 ToolCallResult 列表。",
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="直接支撑结论的证据投影；当前只收集 PolicyRAGTool 文档。",
    )
    draft_final_answer: str | None = Field(default=None, description="安全校验前的答案草稿。")
    verification_result: dict[str, Any] | None = Field(
        default=None,
        description="证据和答案一致性校验结果。",
    )
    safety_result: dict[str, Any] | None = Field(default=None, description="政务安全守卫结果。")
    final_answer: str | None = Field(default=None, description="可返回给用户的最终答案。")
    clarification_question: str | None = Field(
        default=None,
        description="需要用户补充信息时返回的追问文本。",
    )

    @classmethod
    def from_agent_context(
        cls,
        ctx: AgentContext,
        request: RunRequest,
    ) -> WorkflowState:
        """将旧共享上下文转换为新状态快照，供 contract tests 和后续 runtime 迁移使用。

        参数:
            ctx: 旧 Native 编排器推进后的共享上下文。
            request: 与本次上下文对应的框架中立请求信封。

        返回:
            可 JSON 序列化的 `WorkflowState` 快照。
        """

        phase, status, stop_reason = _derive_runtime_position(ctx)
        return cls(
            run_id=request.run_id,
            request_id=request.request_id,
            session_id=request.session_id,
            case_id=request.case_id,
            message_id=request.message_id,
            phase=phase,
            status=status,
            stop_reason=stop_reason,
            capability_call_count=len(ctx.tool_results),
            case_facts=dict(ctx.conversation.active_slots),
            intent_result=ctx.intent_result.model_dump() if ctx.intent_result else None,
            execution_plan=ctx.agent_plan.model_dump() if ctx.agent_plan else None,
            capability_results=[result.model_dump() for result in ctx.tool_results],
            evidence=_collect_evidence(ctx),
            draft_final_answer=ctx.draft_final_answer,
            verification_result=(
                ctx.verification_result.model_dump() if ctx.verification_result else None
            ),
            safety_result=ctx.safety_result.model_dump() if ctx.safety_result else None,
            final_answer=ctx.final_answer,
            clarification_question=_clarification_question(ctx),
        )

    def to_result(self) -> WorkflowResult:
        """生成当前状态对应的运行结果。

        返回:
            面向 CLI、Eval 和未来外部入口的框架中立结果对象。
        """

        return WorkflowResult(
            run_id=self.run_id,
            request_id=self.request_id,
            session_id=self.session_id,
            status=self.status,
            stop_reason=self.stop_reason,
            final_answer=self.final_answer,
            clarification_question=self.clarification_question,
            created_at=now_cn(),
        )


class WorkflowResult(BaseModel):
    """工作流对 CLI、Eval 或未来外部接口暴露的最终结果。"""

    schema_version: Literal["workflow.v1"] = Field(default=SCHEMA_VERSION, description="结果协议版本。")
    run_id: str = Field(description="单次工作流运行 ID。")
    request_id: str = Field(description="用户请求 ID。")
    session_id: str = Field(description="会话 ID。")
    status: RunStatus = Field(description="最终运行状态。")
    stop_reason: StopReason | None = Field(description="最终停止原因；失败和追问必须填写。")
    final_answer: str | None = Field(default=None, description="完成时返回给用户的答案。")
    clarification_question: str | None = Field(default=None, description="追问终止时返回的问题。")
    error_message: str | None = Field(default=None, description="结构化失败时的人类可读错误。")
    created_at: str = Field(default_factory=now_cn, description="结果生成时间。")


class StatePatch(BaseModel):
    """阶段服务返回的状态增量。

    patch_id 用于幂等去重；node_id、logical_call_id 和 attempt 用于把一次逻辑调用、
    节点执行和物理重试关联到 trace。Reducer 是唯一能把 patch 合并进 WorkflowState 的位置。
    """

    patch_id: str = Field(description="状态增量 ID；重复 patch 不得重复追加列表字段。")
    run_id: str = Field(description="patch 所属 run，必须与 WorkflowState.run_id 一致。")
    source_phase: WorkflowPhase = Field(description="产生 patch 时读取的源阶段。")
    next_phase: WorkflowPhase | None = Field(default=None, description="应用成功后的目标阶段。")
    node_id: str = Field(description="产生 patch 的业务节点或阶段服务 ID。")
    logical_call_id: str = Field(description="逻辑调用 ID；同一逻辑重试时保持不变。")
    attempt: int = Field(default=1, ge=1, description="物理尝试次数，从 1 开始递增。")
    fact_updates: dict[str, Any] = Field(
        default_factory=dict,
        description="案件事实增量，按字段覆盖写入 WorkflowState.case_facts。",
    )
    intent_result: dict[str, Any] | None = Field(default=None, description="意图结果覆盖写入。")
    execution_plan: dict[str, Any] | None = Field(default=None, description="执行计划覆盖写入。")
    capability_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="能力结果列表，按 tool_call_id 业务 ID 合并。",
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="证据列表，按 evidence_id 业务 ID 合并。",
    )
    draft_final_answer: str | None = Field(default=None, description="答案草稿覆盖写入。")
    verification_result: dict[str, Any] | None = Field(default=None, description="校验结果覆盖写入。")
    safety_result: dict[str, Any] | None = Field(default=None, description="安全结果覆盖写入。")
    final_answer: str | None = Field(default=None, description="最终答案覆盖写入。")
    clarification_question: str | None = Field(default=None, description="追问文本覆盖写入。")
    status: RunStatus | None = Field(default=None, description="运行状态覆盖写入。")
    stop_reason: StopReason | None = Field(default=None, description="停止原因覆盖写入。")


def _derive_runtime_position(
    ctx: AgentContext,
) -> tuple[WorkflowPhase, RunStatus, StopReason | None]:
    """从旧上下文推导新状态机位置。

    参数:
        ctx: 旧 Native 编排器上下文。

    返回:
        `(phase, status, stop_reason)` 三元组，按业务终止优先级判断。
    """

    # 安全拦截优先级最高；即使已有答案，也不能进入 complete。
    if ctx.safety_result and not ctx.safety_result.passed:
        return WorkflowPhase.SAFETY, RunStatus.STOPPED, StopReason.SAFETY_BLOCKED

    # 能力失败说明 execute 阶段无法正常推进，区别于证据为空的保守回答。
    if any(result.tool_status == "failed" for result in ctx.tool_results):
        return WorkflowPhase.EXECUTE, RunStatus.FAILED, StopReason.CAPABILITY_FAILED

    if _needs_clarification(ctx):
        return WorkflowPhase.CLARIFY, RunStatus.STOPPED, StopReason.NEEDS_CLARIFICATION

    if _has_insufficient_evidence(ctx):
        return (
            WorkflowPhase.VALIDATE_EVIDENCE,
            RunStatus.STOPPED,
            StopReason.INSUFFICIENT_EVIDENCE,
        )

    if ctx.final_answer is not None:
        return WorkflowPhase.COMPLETE, RunStatus.COMPLETED, StopReason.COMPLETE

    return WorkflowPhase.UNDERSTAND, RunStatus.RUNNING, None


def _needs_clarification(ctx: AgentContext) -> bool:
    """判断当前上下文是否需要停在追问阶段。"""

    if ctx.intent_result and ctx.intent_result.ask_clarification:
        return True
    return any(message.status == "need_clarification" for message in ctx.agent_outputs)


def _has_insufficient_evidence(ctx: AgentContext) -> bool:
    """判断是否因缺少可引用证据而停止。"""

    if ctx.verification_result and "missing_citation" in ctx.verification_result.issues:
        return True
    return any(
        result.tool_name == "PolicyRAGTool"
        and result.tool_status == "success"
        and not result.output.get("documents")
        for result in ctx.tool_results
    )


def _clarification_question(ctx: AgentContext) -> str | None:
    """提取对用户展示的追问文本。"""

    if ctx.intent_result and ctx.intent_result.ask_clarification:
        return ctx.intent_result.ask_clarification
    for message in ctx.agent_outputs:
        if message.status == "need_clarification" and message.content:
            return message.content
    return None


def _collect_evidence(ctx: AgentContext) -> list[dict[str, Any]]:
    """从旧 ToolCallResult 中提取支撑答案的证据投影。"""

    evidence: list[dict[str, Any]] = []
    for result in ctx.tool_results:
        if result.tool_name != "PolicyRAGTool" or result.tool_status != "success":
            continue
        for document in result.output.get("documents", []):
            evidence.append(
                {
                    "source": "PolicyRAGTool",
                    "tool_call_id": result.tool_call_id,
                    "document": document,
                }
            )
    return evidence
