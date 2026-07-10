from __future__ import annotations

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.capabilities.contracts import (
    CapabilityGateway,
    CapabilityRequest,
    CapabilityStatus,
)
from ananhu_agent.context.slot_rules import merge_slots
from ananhu_agent.models.model_router import ModelRouter
from ananhu_agent.ports.model_gateway import ModelGatewayError
from ananhu_agent.orchestrator.aggregator import build_final_answer
from ananhu_agent.orchestrator.rules import other_intent_message, revise_intent
from ananhu_agent.orchestrator.safety import PolicySafetyGuard
from ananhu_agent.orchestrator.validators import AnswerValidator
from ananhu_agent.schemas import AgentContext, AgentMessage, AgentPlan, IntentResult, TraceEvent
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.workflow.contracts import (
    RunStatus,
    StatePatch,
    StopReason,
    WorkflowPhase,
    WorkflowState,
)

RUNTIME_NAME = "native"
RUNTIME_VERSION = "native.v1"


class NativeStageServices:
    """Native Runtime 的阶段服务集合。

    每个公开方法只以 `WorkflowState` 作为阶段输入并返回 `StatePatch`。旧
    `AgentContext` 是 Native 内部适配状态，用于复用现有无状态 Agent、Prompt、
    Context 和治理逻辑，不作为 Runtime 端口暴露。
    """

    def __init__(
        self,
        ctx: AgentContext,
        intent_agent: IntentRouterAgent,
        domain_agent: DomainConsultationAgent,
        payment_agent: PaymentCalculationAgent,
        policy_rag_agent: PolicyRAGAgent,
        capability_gateway: CapabilityGateway,
        trace_recorder: TraceRecorder,
        model_router: ModelRouter,
        runtime_name: str = RUNTIME_NAME,
        runtime_version: str = RUNTIME_VERSION,
    ) -> None:
        self.ctx = ctx
        self.intent_agent = intent_agent
        self.domain_agent = domain_agent
        self.payment_agent = payment_agent
        self.policy_rag_agent = policy_rag_agent
        self.capability_gateway = capability_gateway
        self.trace_recorder = trace_recorder
        self.model_router = model_router
        self.runtime_name = runtime_name
        self.runtime_version = runtime_version

    async def understand(self, state: WorkflowState) -> StatePatch:
        self._record(state, "request_received", "understand", {"user_query": state.case_facts["user_query"]})
        model_profile = "intent_fast"
        model_config = self.model_router.get_profile(model_profile)
        model_logical_call_id = f"{state.run_id}:understand:model"
        self._record(state, "model_started", "understand", {
            "model_profile": model_profile,
            "model_config": model_config,
            "prompt_ref": "intent_router.v1",
        }, logical_call_id=model_logical_call_id)
        try:
            intent_message = await self.intent_agent.run(
                self.ctx,
                run_id=state.run_id,
                node_id="understand",
                logical_call_id=model_logical_call_id,
            )
        except ModelGatewayError as exc:
            self._record(state, "model_failed", "understand", {
                "model_profile": model_profile,
                "provider": exc.provider,
                "error_code": exc.code.value,
                "retryable": exc.retryable,
                "status_code": exc.status_code,
            }, logical_call_id=model_logical_call_id)
            raise
        self.ctx.agent_outputs.append(intent_message)
        self._record(
            state,
            "prompt_built",
            "understand",
            {
                "prompt_ref": intent_message.data["prompt_ref"],
                "prompt_metadata": intent_message.data["prompt_metadata"],
                "context_metadata": intent_message.data["context_metadata"],
            },
        )
        self._record(
            state,
            "model_finished",
            "understand",
            {
                "model_profile": model_profile,
                "model_config": model_config,
                "prompt_ref": intent_message.data["prompt_ref"],
                **intent_message.data["model_result"],
            },
            logical_call_id=model_logical_call_id,
        )
        # 保留旧事件名，确保历史 trace 消费方可渐进迁移。
        self._record(state, "model_called", "understand", {
            "model_profile": model_profile,
            "model_config": model_config,
            "prompt_ref": intent_message.data["prompt_ref"],
        }, logical_call_id=model_logical_call_id)
        self._record(state, "intent_recognized", "understand", intent_message.data)
        self._last_intent_message = intent_message
        return StatePatch(
            patch_id=f"{state.run_id}:understand",
            run_id=state.run_id,
            source_phase=WorkflowPhase.UNDERSTAND,
            next_phase=WorkflowPhase.MERGE_FACTS,
            node_id="understand",
            logical_call_id=f"{state.run_id}:understand",
            intent_result=intent_message.data,
        )

    def merge_facts(self, state: WorkflowState) -> StatePatch:
        intent_message = self._last_intent_message
        revised = revise_intent(self.ctx.request.user_query, IntentResult(**intent_message.data))
        active_slots, slot_metadata = merge_slots(self.ctx.conversation.active_slots, revised.slots)
        self.ctx.intent_result = revised
        self.ctx.conversation.active_slots = active_slots
        self.ctx.request.province = active_slots.get("province", self.ctx.request.province)
        self.ctx.request.city = active_slots.get("city", self.ctx.request.city)
        self._record(state, "intent_revised", "merge_facts", revised.model_dump())
        self._record(
            state,
            "slots_merged",
            "merge_facts",
            {"active_slots": active_slots, "metadata": slot_metadata},
        )
        return StatePatch(
            patch_id=f"{state.run_id}:merge_facts",
            run_id=state.run_id,
            source_phase=WorkflowPhase.MERGE_FACTS,
            next_phase=WorkflowPhase.VALIDATE_FACTS,
            node_id="merge_facts",
            logical_call_id=f"{state.run_id}:merge_facts",
            fact_updates=active_slots | {"user_query": self.ctx.request.user_query},
            intent_result=revised.model_dump(),
        )

    def validate_facts(self, state: WorkflowState) -> StatePatch:
        needs_clarification = bool(self.ctx.intent_result and self.ctx.intent_result.ask_clarification)
        next_phase = WorkflowPhase.CLARIFY if needs_clarification else WorkflowPhase.RESOLVE_JURISDICTION
        return StatePatch(
            patch_id=f"{state.run_id}:validate_facts",
            run_id=state.run_id,
            source_phase=WorkflowPhase.VALIDATE_FACTS,
            next_phase=next_phase,
            node_id="validate_facts",
            logical_call_id=f"{state.run_id}:validate_facts",
            clarification_question=(
                self.ctx.intent_result.ask_clarification
                if self.ctx.intent_result and self.ctx.intent_result.ask_clarification
                else None
            ),
            status=RunStatus.STOPPED if needs_clarification else None,
            stop_reason=StopReason.NEEDS_CLARIFICATION if needs_clarification else None,
        )

    def clarify(self, state: WorkflowState) -> StatePatch:
        return StatePatch(
            patch_id=f"{state.run_id}:clarify",
            run_id=state.run_id,
            source_phase=WorkflowPhase.CLARIFY,
            next_phase=WorkflowPhase.COMPLETE,
            node_id="clarify",
            logical_call_id=f"{state.run_id}:clarify",
        )

    def resolve_jurisdiction(self, state: WorkflowState) -> StatePatch:
        return StatePatch(
            patch_id=f"{state.run_id}:resolve_jurisdiction",
            run_id=state.run_id,
            source_phase=WorkflowPhase.RESOLVE_JURISDICTION,
            next_phase=WorkflowPhase.PLAN,
            node_id="resolve_jurisdiction",
            logical_call_id=f"{state.run_id}:resolve_jurisdiction",
            fact_updates={
                key: value
                for key, value in {
                    "province": self.ctx.request.province,
                    "city": self.ctx.request.city,
                }.items()
                if value is not None
            },
        )

    def plan(self, state: WorkflowState) -> StatePatch:
        if self.ctx.intent_result and self.ctx.intent_result.intent == "other":
            # 非领域输入不调用业务 Agent 或能力网关，仍保留后续安全阶段。
            self.ctx.agent_plan = AgentPlan(route_agents=[], required_tools=[])
        elif self.ctx.intent_result and self.ctx.intent_result.intent == "payment_calculation":
            self.ctx.agent_plan = AgentPlan(
                route_agents=["PaymentCalculationAgent", "PolicyRAGAgent"],
                required_tools=["PaymentCalculationTool", "PolicyRAGTool"],
            )
        else:
            self.ctx.agent_plan = AgentPlan(
                route_agents=["DomainConsultationAgent", "PolicyRAGAgent"],
                required_tools=["PolicyRAGTool"],
            )
        return StatePatch(
            patch_id=f"{state.run_id}:plan",
            run_id=state.run_id,
            source_phase=WorkflowPhase.PLAN,
            next_phase=WorkflowPhase.EXECUTE,
            node_id="plan",
            logical_call_id=f"{state.run_id}:plan",
            execution_plan=self.ctx.agent_plan.model_dump(),
        )

    async def execute(self, state: WorkflowState) -> StatePatch:
        if self.ctx.intent_result and self.ctx.intent_result.intent == "other":
            return StatePatch(
                patch_id=f"{state.run_id}:execute",
                run_id=state.run_id,
                source_phase=WorkflowPhase.EXECUTE,
                next_phase=WorkflowPhase.VALIDATE_EVIDENCE,
                node_id="execute",
                logical_call_id=f"{state.run_id}:execute",
            )

        route_message = self._run_business_agent()
        self.ctx.agent_outputs.append(route_message)
        await self._execute_capabilities(state, route_message, "execute")

        policy_message = self.policy_rag_agent.run(self.ctx)
        self.ctx.agent_outputs.append(policy_message)
        await self._execute_capabilities(state, policy_message, "execute")
        return StatePatch(
            patch_id=f"{state.run_id}:execute",
            run_id=state.run_id,
            source_phase=WorkflowPhase.EXECUTE,
            next_phase=WorkflowPhase.VALIDATE_EVIDENCE,
            node_id="execute",
            logical_call_id=f"{state.run_id}:execute",
            capability_results=[result.model_dump() for result in self.ctx.tool_results],
            evidence=_collect_evidence_from_context(self.ctx),
            status=(
                RunStatus.FAILED
                if any(result.tool_status == "failed" for result in self.ctx.tool_results)
                else None
            ),
            stop_reason=(
                StopReason.CAPABILITY_FAILED
                if any(result.tool_status == "failed" for result in self.ctx.tool_results)
                else None
            ),
        )

    def validate_evidence(self, state: WorkflowState) -> StatePatch:
        insufficient = any(
            result.tool_name == "PolicyRAGTool"
            and result.tool_status == "success"
            and not result.output.get("documents")
            for result in self.ctx.tool_results
        )
        return StatePatch(
            patch_id=f"{state.run_id}:validate_evidence",
            run_id=state.run_id,
            source_phase=WorkflowPhase.VALIDATE_EVIDENCE,
            next_phase=WorkflowPhase.COMPOSE,
            node_id="validate_evidence",
            logical_call_id=f"{state.run_id}:validate_evidence",
            status=RunStatus.STOPPED if insufficient else None,
            stop_reason=StopReason.INSUFFICIENT_EVIDENCE if insufficient else None,
        )

    def compose(self, state: WorkflowState) -> StatePatch:
        if self.ctx.intent_result and self.ctx.intent_result.intent == "other":
            self.ctx.final_answer = other_intent_message(self.ctx.request.user_query)
        else:
            self.ctx.final_answer = build_final_answer(self.ctx)
        citations = [
            document["citation"]
            for result in self.ctx.tool_results
            if result.tool_name == "PolicyRAGTool"
            for document in result.output.get("documents", [])
        ]
        self.ctx.verification_result = AnswerValidator().validate(self.ctx.final_answer, citations)
        self._record(state, "answer_validated", "compose", self.ctx.verification_result.model_dump())
        return StatePatch(
            patch_id=f"{state.run_id}:compose",
            run_id=state.run_id,
            source_phase=WorkflowPhase.COMPOSE,
            next_phase=WorkflowPhase.SAFETY,
            node_id="compose",
            logical_call_id=f"{state.run_id}:compose",
            draft_final_answer=self.ctx.final_answer,
            final_answer=self.ctx.final_answer,
            verification_result=self.ctx.verification_result.model_dump(),
        )

    def safety(self, state: WorkflowState) -> StatePatch:
        self.ctx.safety_result = PolicySafetyGuard().check(self.ctx.final_answer or "")
        self._record(state, "safety_checked", "safety", self.ctx.safety_result.model_dump())
        self._record(state, "response_ready", "safety", {"final_answer": self.ctx.final_answer})
        safety_blocked = not self.ctx.safety_result.passed
        return StatePatch(
            patch_id=f"{state.run_id}:safety",
            run_id=state.run_id,
            source_phase=WorkflowPhase.SAFETY,
            next_phase=WorkflowPhase.COMPLETE,
            node_id="safety",
            logical_call_id=f"{state.run_id}:safety",
            safety_result=self.ctx.safety_result.model_dump(),
            status=RunStatus.STOPPED if safety_blocked else RunStatus.COMPLETED,
            stop_reason=StopReason.SAFETY_BLOCKED if safety_blocked else StopReason.COMPLETE,
        )

    def _run_business_agent(self) -> AgentMessage:
        if self.ctx.intent_result and self.ctx.intent_result.intent == "payment_calculation":
            return self.payment_agent.run(self.ctx)
        return self.domain_agent.run(self.ctx)

    async def _execute_capabilities(
        self,
        state: WorkflowState,
        message: AgentMessage,
        node_id: str,
    ) -> None:
        for call in message.tool_calls:
            result = await self.capability_gateway.execute(
                CapabilityRequest(
                    run_id=state.run_id,
                    request_id=self.ctx.request.request_id,
                    session_id=self.ctx.request.session_id,
                    capability_name=call.tool_name,
                    caller=call.called_by,
                    input=call.input,
                    node_id=node_id,
                    logical_call_id=call.tool_call_id,
                    attempt=1,
                    runtime_name=self.runtime_name,
                    runtime_version=self.runtime_version,
                )
            )
            self.ctx.tool_results.append(self._tool_result_from_capability(result))

    @staticmethod
    def _tool_result_from_capability(result):
        from ananhu_agent.schemas import ToolCallResult

        return ToolCallResult(**result.tool_call_result)

    def _record(
        self,
        state: WorkflowState,
        event_type: str,
        phase: str,
        payload: dict,
        logical_call_id: str | None = None,
    ) -> None:
        self.trace_recorder.record(
            TraceEvent.new(
                request_id=state.request_id,
                run_id=state.run_id,
                session_id=state.session_id,
                event_type=event_type,
                phase=phase,
                runtime_name=self.runtime_name,
                runtime_version=self.runtime_version,
                node_id=phase,
                logical_call_id=logical_call_id or f"{state.run_id}:{phase}",
                attempt=1,
                payload=payload,
            )
        )


def _collect_evidence_from_context(ctx: AgentContext) -> list[dict]:
    evidence = []
    for result in ctx.tool_results:
        if result.tool_name != "PolicyRAGTool" or result.tool_status != "success":
            continue
        for index, document in enumerate(result.output.get("documents", []), start=1):
            evidence.append(
                {
                    "evidence_id": f"{result.tool_call_id}:{index}",
                    "source": "PolicyRAGTool",
                    "tool_call_id": result.tool_call_id,
                    "document": document,
                }
            )
    return evidence
