from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.capabilities.contracts import CapabilityGateway
from ananhu_agent.context.slot_rules import extract_user_jurisdiction
from ananhu_agent.models.model_router import ModelRouter
from ananhu_agent.ports.run_event_sink import (
    NodeFailedEvent,
    NodeFailedPayload,
    NodeFinishedEvent,
    NodeFinishedPayload,
    NodeStartedEvent,
    NodeStartedPayload,
    RunCancelledEvent,
    RunCancelledPayload,
    RunEventSink,
    RunFinishedEvent,
    RunFinishedPayload,
    RunStartedEvent,
    RunStartedPayload,
)
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
    StopReason,
    WorkflowPhase,
    WorkflowResult,
    WorkflowRuntime,
    WorkflowState,
)
from ananhu_agent.workflow.reducer import ReducerResult, reduce_workflow_state

RUNTIME_NAME = "native"
RUNTIME_VERSION = "native.v1"


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
        """执行一次 Native run，并由统一边界发布唯一 run 生命周期。"""

        return await _run_with_lifecycle(
            request,
            self.event_sink,
            RUNTIME_NAME,
            RUNTIME_VERSION,
            lambda: self._invoke(request),
        )

    async def _invoke(self, request: RunRequest) -> WorkflowResult:
        """执行 Native 业务阶段，所有增量都经项目 reducer 合并。"""

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
            patch = await _run_stage(stages, phase, state, self.event_sink)
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
                token_usage=_model_usage_summary(ctx),
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
    event_sink: RunEventSink,
):
    """执行共享业务阶段，并保证 started 与唯一 terminal 事件配对。"""

    started = perf_counter()
    event_fields = {
        "run_id": state.run_id,
        "request_id": state.request_id,
        "session_id": state.session_id,
        "node_id": phase.value,
    }
    event_sink.publish(NodeStartedEvent(
        **event_fields,
        public_payload=NodeStartedPayload(
            phase=phase.value,
            input_summary={
                "status": state.status.value,
                "case_fact_keys": sorted(state.case_facts),
                "capability_result_count": len(state.capability_results),
            },
        ),
    ))
    try:
        if phase is WorkflowPhase.UNDERSTAND:
            patch = await stages.understand(state)
        elif phase is WorkflowPhase.EXECUTE:
            patch = await stages.execute(state)
        else:
            patch = getattr(stages, phase.value)(state)
    except BaseException as exc:
        event_sink.publish(NodeFailedEvent(
            **event_fields,
            public_payload=NodeFailedPayload(
                phase=phase.value,
                error_code=(
                    "stage_cancelled"
                    if isinstance(exc, asyncio.CancelledError)
                    else "stage_failed"
                ),
                retryable=False,
                latency_ms=int((perf_counter() - started) * 1000),
                error_message=type(exc).__name__,
            ),
        ))
        raise
    event_sink.publish(NodeFinishedEvent(
        **event_fields,
        public_payload=NodeFinishedPayload(
            phase=phase.value,
            latency_ms=int((perf_counter() - started) * 1000),
            patch_summary={
                "source_phase": patch.source_phase.value,
                "next_phase": patch.next_phase.value if patch.next_phase else None,
                "status": patch.status.value if patch.status else None,
                "fact_update_keys": sorted(patch.fact_updates),
                "capability_result_count": len(patch.capability_results),
                "evidence_count": len(patch.evidence),
            },
        ),
    ))
    return patch


async def _run_with_lifecycle(
    request: RunRequest,
    event_sink: RunEventSink,
    runtime_name: str,
    runtime_version: str,
    operation: Callable[[], Awaitable[WorkflowResult]],
) -> WorkflowResult:
    """统一 run 生命周期，确保取消和异常也由唯一终止屏障收束。"""

    started = perf_counter()
    result: WorkflowResult | None = None
    status = RunStatus.FAILED.value
    stop_reason = "runtime_failed"
    event_fields = {
        "run_id": request.run_id,
        "request_id": request.request_id,
        "session_id": request.session_id,
    }
    event_sink.publish(RunStartedEvent(
        **event_fields,
        public_payload=RunStartedPayload(
            runtime_name=runtime_name,
            runtime_version=runtime_version,
        ),
    ))
    try:
        result = await operation()
        status = result.status.value
        stop_reason = result.stop_reason.value if result.stop_reason else "unknown"
        return result
    except asyncio.CancelledError:
        status = RunStatus.CANCELLED.value
        stop_reason = StopReason.USER_CANCELLED.value
        event_sink.publish(RunCancelledEvent(
            **event_fields,
            public_payload=RunCancelledPayload(),
        ))
        raise
    finally:
        final_state = None
        if result and result.final_state:
            final_state = {
                "phase": result.final_state.phase.value,
                "status": result.final_state.status.value,
                "stop_reason": (
                    result.final_state.stop_reason.value
                    if result.final_state.stop_reason
                    else None
                ),
            }
        event_sink.publish(RunFinishedEvent(
            **event_fields,
            public_payload=RunFinishedPayload(
                status=status,
                stop_reason=stop_reason,
                final_state=final_state,
                latency_ms=int((perf_counter() - started) * 1000),
            ),
        ))


def _model_usage_summary(ctx: AgentContext) -> dict:
    """汇总项目 ModelResult，Fake 与真实 provider 保持不同来源标识。"""

    results = [
        message.data["model_result"]
        for message in ctx.agent_outputs
        if "model_result" in message.data
    ]
    if not results:
        return {}
    usages = [result["usage"] for result in results]
    sources = {usage["usage_source"] for usage in usages}
    estimated_costs = [usage["estimated_cost"] for usage in usages]
    currencies = {usage["currency"] for usage in usages if usage["currency"]}
    return {
        "usage_source": next(iter(sources)) if len(sources) == 1 else "mixed",
        "input_tokens": sum(usage["input_tokens"] for usage in usages),
        "output_tokens": sum(usage["output_tokens"] for usage in usages),
        "cache_tokens": sum(usage["cache_tokens"] for usage in usages),
        "total_tokens": sum(usage["total_tokens"] for usage in usages),
        "estimated_cost": (
            round(sum(cost for cost in estimated_costs if cost is not None), 8)
            if estimated_costs and all(cost is not None for cost in estimated_costs)
            else None
        ),
        "currency": next(iter(currencies)) if len(currencies) == 1 else None,
        "calls": len(results),
    }


def _context_from_request(request: RunRequest) -> AgentContext:
    trusted_jurisdiction = dict(request.trusted_jurisdiction)
    if not trusted_jurisdiction:
        trusted_jurisdiction = extract_user_jurisdiction(request.user_query)
    ctx = AgentContext.new_for_query(
        session_id=request.session_id,
        turn_id=request.turn_id,
        user_query=request.user_query,
        province=trusted_jurisdiction.get("province"),
        city=trusted_jurisdiction.get("city"),
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
