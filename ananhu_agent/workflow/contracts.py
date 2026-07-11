from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from ananhu_agent.schemas import now_cn

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
    CANCELLED = "cancelled"


class StopReason(str, Enum):
    """运行终止原因，供 Native 和后续 LangGraph Runtime 共同遵守。"""

    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CAPABILITY_FAILED = "capability_failed"
    SAFETY_BLOCKED = "safety_blocked"
    USER_CANCELLED = "user_cancelled"


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
    request_id: str = Field(description="用户一次请求的根关联 ID。")
    session_id: str = Field(description="多轮会话 ID，用于关联 SessionState 和对话记忆。")
    case_id: str | None = Field(
        default=None,
        description="跨会话案件事实 ID；当前 CLI MVP 尚未持久化 CaseRecord。",
    )
    message_id: str | None = Field(
        default=None,
        description="外部消息或 CLI turn 的 ID；当前可为空，供后续外部入口对齐。",
    )
    turn_id: int = Field(description="会话内轮次。")
    user_query: str = Field(description="当前用户原始问题，后续上下文裁剪不得丢弃。")
    input_type: Literal["text"] = Field(default="text", description="当前 MVP 只支持文本输入。")
    trusted_jurisdiction: dict[str, str | None] = Field(
        default_factory=dict,
        description="由编排器确认后的可信地区，不让 Agent 自行决定政策适用边界。",
    )
    created_at: str = Field(description="请求创建时间，沿用中国时区 trace 时间格式。")


class WorkflowState(BaseModel):
    """单次 run 的可序列化业务状态投影。

    状态只由项目 Runtime 和 reducer 推进，不提供共享上下文映射。
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
        description="能力执行结果；当前保存能力网关返回的工具结果投影。",
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="直接支撑结论的 EvidenceItem 投影，按 evidence_id 合并。",
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
    final_state: WorkflowState | None = Field(
        default=None,
        description="最终状态快照；CLI 可忽略，Eval 用它读取框架中立指标。",
    )


class WorkflowRuntime(ABC):
    """工作流运行时端口，CLI/Eval 只能依赖该抽象。

    Native 和后续 LangGraph Runtime 都实现该端口。端口只暴露项目协议类型，
    不泄漏具体调度框架或底层工具执行类型。
    """

    @abstractmethod
    async def invoke(self, request: RunRequest) -> WorkflowResult:
        """执行一次工作流运行并返回框架中立结果。"""


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
        description="能力结果列表，按 logical_call_id 业务 ID 合并。",
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
