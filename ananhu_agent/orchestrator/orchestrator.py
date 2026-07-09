from __future__ import annotations

from pathlib import Path

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.context.slot_rules import merge_slots
from ananhu_agent.models.fake_model import FakeModelClient
from ananhu_agent.orchestrator.aggregator import build_final_answer
from ananhu_agent.orchestrator.rules import revise_intent
from ananhu_agent.orchestrator.safety import PolicySafetyGuard
from ananhu_agent.orchestrator.validators import AnswerValidator
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import (
    AgentContext,
    AgentMessage,
    AgentPlan,
    IntentResult,
    RunReport,
    TaskState,
    ToolCallResult,
    TraceEvent,
)
from ananhu_agent.storage.runtime_stores import ReportStore, TaskStateStore, TraceRecorder
from ananhu_agent.tools.executor import ToolExecutor
from ananhu_agent.tools.payment_calculation import calculate_payment
from ananhu_agent.tools.policy_rag import search_policy
from ananhu_agent.tools.registry import ToolDefinition, ToolRegistry


class AgentOrchestrator:
    """单轮同步编排器，负责上下文推进、工具执行和运行证据落盘。"""

    def __init__(
        self,
        intent_agent: IntentRouterAgent,
        domain_agent: DomainConsultationAgent,
        payment_agent: PaymentCalculationAgent,
        policy_rag_agent: PolicyRAGAgent,
        tool_executor: ToolExecutor,
        trace_recorder: TraceRecorder,
        task_state_store: TaskStateStore,
        report_store: ReportStore,
    ) -> None:
        self.intent_agent = intent_agent
        self.domain_agent = domain_agent
        self.payment_agent = payment_agent
        self.policy_rag_agent = policy_rag_agent
        self.tool_executor = tool_executor
        self.trace_recorder = trace_recorder
        self.task_state_store = task_state_store
        self.report_store = report_store

    def ask(self, session_id: str, turn_id: int, user_query: str) -> AgentContext:
        """执行一轮从用户问题到最终答案的同步咨询链路。"""

        ctx = AgentContext.new_for_query(session_id, turn_id, user_query)
        self._record(ctx, "request_received", "orchestrator", {"user_query": user_query})

        intent_message = self._run_intent_agent(ctx)
        ctx.intent_result = self._revise_and_merge_slots(ctx, intent_message)
        route_message = self._run_business_agent(ctx)
        self._execute_tool_calls(ctx, route_message)

        policy_message = self.policy_rag_agent.run(ctx)
        ctx.agent_outputs.append(policy_message)
        self._execute_tool_calls(ctx, policy_message)

        ctx.final_answer = build_final_answer(ctx)
        citations = self._collect_citations(ctx.tool_results)
        ctx.verification_result = AnswerValidator().validate(ctx.final_answer, citations)
        self._record(ctx, "answer_validated", "validation", ctx.verification_result.model_dump())

        ctx.safety_result = PolicySafetyGuard().check(ctx.final_answer)
        self._record(ctx, "safety_checked", "safety", ctx.safety_result.model_dump())
        self._record(ctx, "response_ready", "orchestrator", {"final_answer": ctx.final_answer})

        self._append_runtime_evidence(ctx, intent_message)
        return ctx

    def _run_intent_agent(self, ctx: AgentContext) -> AgentMessage:
        intent_message = self.intent_agent.run(ctx)
        ctx.agent_outputs.append(intent_message)
        self._record(
            ctx,
            "prompt_built",
            "prompt",
            {
                "prompt_ref": intent_message.data["prompt_ref"],
                "prompt_metadata": intent_message.data["prompt_metadata"],
                "context_metadata": intent_message.data["context_metadata"],
            },
        )
        self._record(
            ctx,
            "model_called",
            "model",
            {"model_profile": "intent_fast", "prompt_ref": intent_message.data["prompt_ref"]},
        )
        self._record(ctx, "intent_recognized", "routing", intent_message.data)
        return intent_message

    def _revise_and_merge_slots(
        self,
        ctx: AgentContext,
        intent_message: AgentMessage,
    ) -> IntentResult:
        revised = revise_intent(ctx.request.user_query, IntentResult(**intent_message.data))
        active_slots, slot_metadata = merge_slots(ctx.conversation.active_slots, revised.slots)
        ctx.conversation.active_slots = active_slots
        self._sync_request_region(ctx)
        self._record(ctx, "intent_revised", "routing", revised.model_dump())
        self._record(
            ctx,
            "slots_merged",
            "routing",
            {"active_slots": active_slots, "metadata": slot_metadata},
        )
        return revised

    def _sync_request_region(self, ctx: AgentContext) -> None:
        # 地区槽位决定政策适用边界；由编排器统一推进给后续无状态 Agent 读取。
        ctx.request.province = ctx.conversation.active_slots.get("province", ctx.request.province)
        ctx.request.city = ctx.conversation.active_slots.get("city", ctx.request.city)

    def _run_business_agent(self, ctx: AgentContext) -> AgentMessage:
        if ctx.intent_result and ctx.intent_result.intent == "payment_calculation":
            ctx.agent_plan = AgentPlan(
                route_agents=["PaymentCalculationAgent", "PolicyRAGAgent"],
                required_tools=["PaymentCalculationTool", "PolicyRAGTool"],
            )
            message = self.payment_agent.run(ctx)
        else:
            ctx.agent_plan = AgentPlan(
                route_agents=["DomainConsultationAgent", "PolicyRAGAgent"],
                required_tools=["PolicyRAGTool"],
            )
            message = self.domain_agent.run(ctx)
        ctx.agent_outputs.append(message)
        return message

    def _execute_tool_calls(self, ctx: AgentContext, message: AgentMessage) -> None:
        for call in message.tool_calls:
            ctx.tool_results.append(
                self.tool_executor.execute(
                    ctx.request.request_id,
                    ctx.request.session_id,
                    call,
                )
            )

    def _append_runtime_evidence(self, ctx: AgentContext, intent_message: AgentMessage) -> None:
        fallback_used = any(result.fallback_used for result in ctx.tool_results)
        prompt_ref = intent_message.data["prompt_ref"]
        self.task_state_store.append(
            TaskState(
                id=f"state_{ctx.request.request_id}",
                session_id=ctx.request.session_id,
                turn_id=ctx.request.turn_id,
                user_query=ctx.request.user_query,
                status="completed",
                current_phase="response_ready",
                raw_intent=intent_message.data["intent"],
                revised_intent=ctx.intent_result.intent if ctx.intent_result else None,
                active_slots=ctx.conversation.active_slots,
                missing_slots=ctx.intent_result.missing_slots if ctx.intent_result else [],
                route_agents=ctx.agent_plan.route_agents if ctx.agent_plan else [],
                prompt_refs=[prompt_ref],
                tool_steps=[result.tool_name for result in ctx.tool_results],
                model_attempts=1,
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
                model_attempts=1,
                prompt_refs=[prompt_ref],
                prompt_metadata={prompt_ref: intent_message.data["prompt_metadata"]},
                output_schema_valid_rate=1.0 if ctx.verification_result.passed else 0.0,
                token_usage={},
                latency_ms=0,
                fallback_used=fallback_used,
                safety_result=ctx.safety_result.model_dump(),
                badcase_candidate=not ctx.verification_result.passed or not ctx.safety_result.passed,
            )
        )

    def _record(
        self,
        ctx: AgentContext,
        event_type: str,
        phase: str,
        payload: dict,
    ) -> None:
        self.trace_recorder.record(
            TraceEvent.new(
                request_id=ctx.request.request_id,
                session_id=ctx.request.session_id,
                event_type=event_type,
                phase=phase,
                payload=payload,
            )
        )

    @staticmethod
    def _collect_citations(tool_results: list[ToolCallResult]) -> list[dict]:
        return [
            document["citation"]
            for result in tool_results
            if result.tool_name == "PolicyRAGTool"
            for document in result.output.get("documents", [])
        ]


def create_default_orchestrator(base_path: Path) -> AgentOrchestrator:
    """创建 MVP 默认运行时装配，供 CLI、测试和后续 eval 复用。"""

    trace_recorder = TraceRecorder(base_path / "traces.jsonl")
    task_state_store = TaskStateStore(base_path / "task_states.jsonl")
    report_store = ReportStore(base_path / "run_reports.jsonl")
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索工伤法规、地方政策、办事指南",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            handler=search_policy,
        )
    )
    registry.register(
        ToolDefinition(
            name="PaymentCalculationTool",
            description="工伤待遇测算",
            risk_level="calculation",
            timeout_ms=3000,
            allowed_callers=["PaymentCalculationAgent"],
            required_input_keys=["disability_grade", "monthly_wage"],
            handler=calculate_payment,
        )
    )
    return AgentOrchestrator(
        intent_agent=IntentRouterAgent(
            FakeModelClient(),
            ContextManager(),
            PromptManager(Path("ananhu_agent/prompts/templates")),
        ),
        domain_agent=DomainConsultationAgent(),
        payment_agent=PaymentCalculationAgent(),
        policy_rag_agent=PolicyRAGAgent(),
        tool_executor=ToolExecutor(registry, trace_recorder),
        trace_recorder=trace_recorder,
        task_state_store=task_state_store,
        report_store=report_store,
    )
