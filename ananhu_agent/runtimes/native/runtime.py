from __future__ import annotations

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.capabilities.contracts import CapabilityGateway
from ananhu_agent.models.model_router import ModelRouter
from ananhu_agent.runtimes.native.stages import NativeStageServices
from ananhu_agent.schemas import (
    AgentContext,
    BadcaseRecord,
    RunReport,
    SessionState,
    TaskState,
    now_cn,
)
from ananhu_agent.orchestrator.badcase_rules import detect_badcase_issues
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
    WorkflowPhase,
    WorkflowResult,
    WorkflowRuntime,
    WorkflowState,
)
from ananhu_agent.workflow.reducer import ReducerResult, reduce_workflow_state


class NativeWorkflowRuntime(WorkflowRuntime):
    """使用项目 reducer 串行推进业务阶段的 Native Runtime。"""

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

    async def invoke(self, request: RunRequest) -> WorkflowResult:
        """执行一次 Native run，所有阶段增量都经项目 reducer 合并。"""

        ctx = _context_from_request(request)
        self._restore_session_state(ctx)
        state = _initial_state(request)
        stages = NativeStageServices(
            ctx=ctx,
            intent_agent=self.intent_agent,
            domain_agent=self.domain_agent,
            payment_agent=self.payment_agent,
            policy_rag_agent=self.policy_rag_agent,
            capability_gateway=self.capability_gateway,
            trace_recorder=self.trace_recorder,
            model_router=self.model_router,
        )

        for phase in (
            WorkflowPhase.UNDERSTAND,
            WorkflowPhase.MERGE_FACTS,
            WorkflowPhase.VALIDATE_FACTS,
            WorkflowPhase.CLARIFY,
            WorkflowPhase.RESOLVE_JURISDICTION,
            WorkflowPhase.PLAN,
            WorkflowPhase.EXECUTE,
            WorkflowPhase.VALIDATE_EVIDENCE,
            WorkflowPhase.COMPOSE,
            WorkflowPhase.SAFETY,
        ):
            if state.phase is not phase:
                continue
            patch = await _run_stage(stages, phase, state)
            reduced = reduce_workflow_state(state, patch)
            if not reduced.ok:
                return _failed_result(request, state, reduced)
            state = reduced.state
            if state.phase is WorkflowPhase.COMPLETE or state.status is not RunStatus.RUNNING:
                break

        self._append_session_state(ctx)
        badcase_issues = detect_badcase_issues(state)
        self._append_automatic_badcases(ctx, badcase_issues)
        self._append_runtime_evidence(ctx, badcase_issues)
        result = state.to_result()
        return result.model_copy(update={"final_state": state}, deep=True)

    def _restore_session_state(self, ctx: AgentContext) -> None:
        latest = self.session_state_store.get_latest(ctx.request.session_id)
        if latest is None:
            return
        ctx.conversation.history_summary = latest.history_summary
        ctx.conversation.last_user_intent = latest.last_user_intent
        ctx.conversation.last_answer_summary = latest.last_answer_summary
        ctx.conversation.active_slots = dict(latest.active_slots)

    def _append_session_state(self, ctx: AgentContext) -> None:
        self.session_state_store.append(
            SessionState(
                session_id=ctx.request.session_id,
                turn_id=ctx.request.turn_id,
                history_summary=ctx.conversation.history_summary,
                last_user_intent=ctx.intent_result.intent if ctx.intent_result else None,
                last_answer_summary=(ctx.final_answer or "")[:120],
                active_slots=ctx.conversation.active_slots,
                updated_at=now_cn(),
            )
        )

    def _append_automatic_badcases(self, ctx: AgentContext, issues: list[str]) -> None:
        for issue in issues:
            self.badcase_store.append(
                BadcaseRecord(
                    id=f"badcase_{ctx.request.request_id}_{issue}",
                    request_id=ctx.request.request_id,
                    session_id=ctx.request.session_id,
                    turn_id=ctx.request.turn_id,
                    query=ctx.request.user_query,
                    predicted_intent=ctx.intent_result.intent if ctx.intent_result else None,
                    issue_type=issue,
                    agent_route=ctx.agent_plan.route_agents if ctx.agent_plan else [],
                    tool_calls=[result.tool_name for result in ctx.tool_results],
                    actual_answer=ctx.final_answer or "",
                    expected_answer="",
                    correction_note="system_auto_candidate",
                    added_to_eval=False,
                    fixed=False,
                    created_at=now_cn(),
                )
            )

    def _append_runtime_evidence(self, ctx: AgentContext, badcase_issues: list[str]) -> None:
        fallback_used = any(result.fallback_used for result in ctx.tool_results)
        prompt_refs = [
            message.data["prompt_ref"]
            for message in ctx.agent_outputs
            if "prompt_ref" in message.data
        ]
        prompt_ref = prompt_refs[0] if prompt_refs else ""
        self.task_state_store.append(
            TaskState(
                id=f"state_{ctx.request.request_id}",
                session_id=ctx.request.session_id,
                turn_id=ctx.request.turn_id,
                user_query=ctx.request.user_query,
                status="completed",
                current_phase="response_ready",
                raw_intent=ctx.intent_result.intent if ctx.intent_result else None,
                revised_intent=ctx.intent_result.intent if ctx.intent_result else None,
                active_slots=ctx.conversation.active_slots,
                missing_slots=ctx.intent_result.missing_slots if ctx.intent_result else [],
                route_agents=ctx.agent_plan.route_agents if ctx.agent_plan else [],
                prompt_refs=prompt_refs,
                tool_steps=[result.tool_name for result in ctx.tool_results],
                model_attempts=1 if prompt_ref else 0,
                fallback_used=fallback_used,
                error_message=None,
            )
        )
        self.report_store.append(
            RunReport(
                id=f"report_{ctx.request.request_id}",
                session_id=ctx.request.session_id,
                final_status="success",
                final_intent=ctx.intent_result.intent if ctx.intent_result else None,
                route_agents=ctx.agent_plan.route_agents if ctx.agent_plan else [],
                tool_count=len(ctx.tool_results),
                model_attempts=1 if prompt_ref else 0,
                prompt_refs=prompt_refs,
                prompt_metadata={
                    message.data["prompt_ref"]: message.data["prompt_metadata"]
                    for message in ctx.agent_outputs
                    if "prompt_ref" in message.data
                },
                output_schema_valid_rate=(
                    1.0 if ctx.verification_result and ctx.verification_result.passed else 0.0
                ),
                token_usage={},
                latency_ms=0,
                fallback_used=fallback_used,
                safety_result=ctx.safety_result.model_dump() if ctx.safety_result else {},
                badcase_candidate=bool(badcase_issues),
            )
        )


async def _run_stage(
    stages: NativeStageServices,
    phase: WorkflowPhase,
    state: WorkflowState,
):
    if phase is WorkflowPhase.EXECUTE:
        return await stages.execute(state)
    return getattr(stages, phase.value)(state)


def _context_from_request(request: RunRequest) -> AgentContext:
    ctx = AgentContext.new_for_query(
        session_id=request.session_id,
        turn_id=request.turn_id,
        user_query=request.user_query,
        province=request.trusted_jurisdiction.get("province"),
        city=request.trusted_jurisdiction.get("city"),
    )
    ctx.request.request_id = request.request_id
    ctx.request.created_at = request.created_at
    return ctx


def _initial_state(request: RunRequest) -> WorkflowState:
    return WorkflowState(
        run_id=request.run_id,
        request_id=request.request_id,
        session_id=request.session_id,
        case_id=request.case_id,
        message_id=request.message_id,
        case_facts={
            "user_query": request.user_query,
            "turn_id": request.turn_id,
            **request.trusted_jurisdiction,
        },
    )


def _failed_result(
    request: RunRequest,
    state: WorkflowState,
    reduced: ReducerResult,
) -> WorkflowResult:
    return WorkflowResult(
        run_id=request.run_id,
        request_id=request.request_id,
        session_id=request.session_id,
        status=RunStatus.FAILED,
        stop_reason=state.stop_reason,
        error_message=reduced.error_message,
        final_state=state,
    )
