from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.capabilities.contracts import CapabilityGateway
from ananhu_agent.models.model_router import ModelRouter
from ananhu_agent.orchestrator.badcase_rules import detect_badcase_issues
from ananhu_agent.ports.run_event_sink import RunEventSink
from ananhu_agent.runtimes.native.runtime import (
    _context_from_request,
    _initial_state,
    _model_usage_summary,
    _run_stage,
    _run_with_lifecycle,
)
from ananhu_agent.runtimes.native.stages import NativeStageServices
from ananhu_agent.schemas import BadcaseRecord, RunReport, SessionState, TaskState, now_cn
from ananhu_agent.storage.runtime_stores import (
    BadcaseStore,
    ReportStore,
    SessionStateStore,
    TaskStateStore,
    TraceRecorder,
)
from ananhu_agent.workflow.contracts import (
    RunRequest,
    RunStatus,
    StatePatch,
    WorkflowPhase,
    WorkflowResult,
    WorkflowRuntime,
    WorkflowState,
)
from ananhu_agent.workflow.reducer import reduce_workflow_state

RUNTIME_NAME = "langgraph"
RUNTIME_VERSION = "langgraph.v1"


class LangGraphState(TypedDict):
    """图内部投影，只保存项目状态和项目 patch，不定义业务字段或 reducer。"""

    state: WorkflowState
    patch: StatePatch | None
    reducer_error: str | None


class LangGraphWorkflowRuntime(WorkflowRuntime):
    """使用 LangGraph 调度稳定业务阶段的最小串行 Runtime。

    节点仅调用既有阶段服务并返回 `StatePatch`；`apply_patch` 节点是唯一调用项目
    reducer 的位置。图不启用 ToolNode、checkpoint、interrupt 或并行执行。
    """

    def __init__(
        self,
        intent_agent: IntentRouterAgent,
        domain_agent: DomainConsultationAgent,
        payment_agent: PaymentCalculationAgent,
        policy_rag_agent: PolicyRAGAgent,
        capability_gateway: CapabilityGateway,
        trace_recorder: TraceRecorder,
        task_state_store: TaskStateStore,
        report_store: ReportStore,
        session_state_store: SessionStateStore,
        badcase_store: BadcaseStore,
        model_router: ModelRouter,
        event_sink: RunEventSink,
    ) -> None:
        self.intent_agent = intent_agent
        self.domain_agent = domain_agent
        self.payment_agent = payment_agent
        self.policy_rag_agent = policy_rag_agent
        self.capability_gateway = capability_gateway
        self.trace_recorder = trace_recorder
        self.task_state_store = task_state_store
        self.report_store = report_store
        self.session_state_store = session_state_store
        self.badcase_store = badcase_store
        self.model_router = model_router
        self.event_sink = event_sink

    async def invoke(self, request: RunRequest) -> WorkflowResult:
        """运行 LangGraph 图，并复用项目统一的 run 生命周期。"""

        return await _run_with_lifecycle(
            request,
            self.event_sink,
            RUNTIME_NAME,
            RUNTIME_VERSION,
            lambda: self._invoke(request),
        )

    async def _invoke(self, request: RunRequest) -> WorkflowResult:
        """运行一张仅调度项目阶段的 LangGraph 图。"""

        ctx = _context_from_request(request)
        self._restore_session_state(ctx)
        stages = NativeStageServices(
            ctx=ctx,
            intent_agent=self.intent_agent,
            domain_agent=self.domain_agent,
            payment_agent=self.payment_agent,
            policy_rag_agent=self.policy_rag_agent,
            capability_gateway=self.capability_gateway,
            trace_recorder=self.trace_recorder,
            model_router=self.model_router,
            runtime_name=RUNTIME_NAME,
            runtime_version=RUNTIME_VERSION,
        )
        output = await _build_graph(stages, self.event_sink).ainvoke(
            {"state": _initial_state(request), "patch": None, "reducer_error": None}
        )
        state = output["state"]
        self._append_session_state(ctx)
        badcase_issues = detect_badcase_issues(state)
        self._append_automatic_badcases(ctx, badcase_issues)
        self._append_runtime_evidence(ctx, badcase_issues)
        if output.get("reducer_error"):
            return WorkflowResult(
                run_id=request.run_id,
                request_id=request.request_id,
                session_id=request.session_id,
                status=RunStatus.FAILED,
                stop_reason=state.stop_reason,
                error_message=output["reducer_error"],
                final_state=state,
            )
        return state.to_result().model_copy(update={"final_state": state}, deep=True)

    def _restore_session_state(self, ctx) -> None:
        latest = self.session_state_store.get_latest(ctx.request.session_id)
        if latest is not None:
            ctx.conversation.history_summary = latest.history_summary
            ctx.conversation.last_user_intent = latest.last_user_intent
            ctx.conversation.last_answer_summary = latest.last_answer_summary
            ctx.conversation.active_slots = dict(latest.active_slots)

    def _append_session_state(self, ctx) -> None:
        self.session_state_store.append(SessionState(
            session_id=ctx.request.session_id, turn_id=ctx.request.turn_id,
            history_summary=ctx.conversation.history_summary,
            last_user_intent=ctx.intent_result.intent if ctx.intent_result else None,
            last_answer_summary=(ctx.final_answer or "")[:120],
            active_slots=ctx.conversation.active_slots, updated_at=now_cn(),
        ))

    def _append_automatic_badcases(self, ctx, issues: list[str]) -> None:
        for issue in issues:
            self.badcase_store.append(BadcaseRecord(
                id=f"badcase_{ctx.request.request_id}_{issue}", request_id=ctx.request.request_id,
                session_id=ctx.request.session_id, turn_id=ctx.request.turn_id,
                query=ctx.request.user_query,
                predicted_intent=ctx.intent_result.intent if ctx.intent_result else None,
                issue_type=issue, agent_route=ctx.agent_plan.route_agents if ctx.agent_plan else [],
                capability_calls=[
                    result.capability_name for result in ctx.capability_results
                ], actual_answer=ctx.final_answer or "",
                expected_answer="", correction_note="system_auto_candidate", added_to_eval=False,
                fixed=False, created_at=now_cn(),
            ))

    def _append_runtime_evidence(self, ctx, badcase_issues: list[str]) -> None:
        prompt_refs = [message.data["prompt_ref"] for message in ctx.agent_outputs if "prompt_ref" in message.data]
        prompt_ref = prompt_refs[0] if prompt_refs else ""
        fallback_used = any(
            result.status.value == "failed" for result in ctx.capability_results
        )
        self.task_state_store.append(TaskState(
            id=f"state_{ctx.request.request_id}", session_id=ctx.request.session_id,
            turn_id=ctx.request.turn_id, user_query=ctx.request.user_query, status="completed",
            current_phase="response_ready", raw_intent=ctx.intent_result.intent if ctx.intent_result else None,
            revised_intent=ctx.intent_result.intent if ctx.intent_result else None,
            active_slots=ctx.conversation.active_slots,
            missing_slots=ctx.intent_result.missing_slots if ctx.intent_result else [],
            route_agents=ctx.agent_plan.route_agents if ctx.agent_plan else [], prompt_refs=prompt_refs,
            capability_steps=[
                result.capability_name for result in ctx.capability_results
            ], model_attempts=1 if prompt_ref else 0,
            fallback_used=fallback_used, error_message=None,
        ))
        self.report_store.append(RunReport(
            id=f"report_{ctx.request.request_id}", session_id=ctx.request.session_id,
            final_status="success", final_intent=ctx.intent_result.intent if ctx.intent_result else None,
            route_agents=ctx.agent_plan.route_agents if ctx.agent_plan else [],
            capability_count=len(ctx.capability_results),
            model_attempts=1 if prompt_ref else 0, prompt_refs=prompt_refs,
            prompt_metadata={message.data["prompt_ref"]: message.data["prompt_metadata"] for message in ctx.agent_outputs if "prompt_ref" in message.data},
            output_schema_valid_rate=1.0 if ctx.verification_result and ctx.verification_result.passed else 0.0,
            token_usage=_model_usage_summary(ctx), latency_ms=0, fallback_used=fallback_used,
            safety_result=ctx.safety_result.model_dump() if ctx.safety_result else {},
            badcase_candidate=bool(badcase_issues),
        ))


def _build_graph(stages: NativeStageServices, event_sink: RunEventSink):
    """构造每次 run 独立的串行图，闭包只捕获本次运行的阶段服务。"""

    graph = StateGraph(LangGraphState)
    phases = tuple(phase for phase in WorkflowPhase if phase is not WorkflowPhase.COMPLETE)

    for phase in phases:
        graph.add_node(phase.value, _stage_node(stages, phase, event_sink))
    graph.add_node("apply_patch", _apply_patch)
    graph.add_edge(START, WorkflowPhase.UNDERSTAND.value)
    for phase in phases:
        graph.add_edge(phase.value, "apply_patch")
    graph.add_conditional_edges("apply_patch", _route_next_phase)
    return graph.compile()


def _stage_node(
    stages: NativeStageServices,
    phase: WorkflowPhase,
    event_sink: RunEventSink,
):
    async def node(graph_state: LangGraphState) -> dict[str, StatePatch | None]:
        return {
            "patch": await _run_stage(
                stages,
                phase,
                graph_state["state"],
                event_sink,
            )
        }

    return node


def _apply_patch(graph_state: LangGraphState) -> dict:
    patch = graph_state["patch"]
    if patch is None:
        return {}
    reduced = reduce_workflow_state(graph_state["state"], patch)
    if not reduced.ok:
        return {"reducer_error": reduced.error_message}
    return {"state": reduced.state, "patch": None}


def _route_next_phase(graph_state: LangGraphState) -> str:
    if graph_state.get("reducer_error") or graph_state["state"].status is not RunStatus.RUNNING:
        return END
    if graph_state["state"].phase is WorkflowPhase.COMPLETE:
        return END
    return graph_state["state"].phase.value
