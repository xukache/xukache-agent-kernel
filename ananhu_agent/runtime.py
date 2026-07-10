from __future__ import annotations

from pathlib import Path

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.capabilities.tool_executor_gateway import ToolExecutorCapabilityGateway
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.models.model_router import ModelRouter
from ananhu_agent.ports.run_event_sink import NoOpRunEventSink, RunEventSink
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.runtimes.native.runtime import NativeWorkflowRuntime
from ananhu_agent.storage.runtime_stores import (
    BadcaseStore,
    ReportStore,
    SessionStateStore,
    TaskStateStore,
    TraceRecorder,
)
from ananhu_agent.tools.executor import ToolExecutor
from ananhu_agent.tools.payment_calculation import calculate_payment
from ananhu_agent.tools.policy_rag import search_policy
from ananhu_agent.tools.registry import ToolDefinition, ToolRegistry
from ananhu_agent.workflow.contracts import WorkflowRuntime


def create_default_runtime(
    base_path: Path,
    settings: RuntimeSettings | None = None,
    event_sink: RunEventSink | None = None,
) -> WorkflowRuntime:
    """创建默认 WorkflowRuntime。

    默认装配 LangGraph Runtime，也可通过 RuntimeSettings 显式选择 Native；
    CLI/Eval 始终只依赖框架中立端口。
    """

    settings = settings or RuntimeSettings(runtime_dir=base_path)
    event_sink = event_sink or NoOpRunEventSink()
    model_router = ModelRouter(settings)
    trace_recorder = TraceRecorder(base_path / "traces.jsonl")
    registry = _default_tool_registry()
    tool_executor = ToolExecutor(registry, trace_recorder)
    capability_gateway = ToolExecutorCapabilityGateway(tool_executor, event_sink=event_sink)
    runtime_kwargs = dict(
        intent_agent=IntentRouterAgent(
            model_router.gateway_for("intent_fast"),
            ContextManager(),
            PromptManager(settings.prompt_template_dir),
        ),
        domain_agent=DomainConsultationAgent(),
        payment_agent=PaymentCalculationAgent(),
        policy_rag_agent=PolicyRAGAgent(),
        capability_gateway=capability_gateway,
        trace_recorder=trace_recorder,
        task_state_store=TaskStateStore(base_path / "task_states.jsonl"),
        report_store=ReportStore(base_path / "run_reports.jsonl"),
        session_state_store=SessionStateStore(base_path / "session_states.jsonl"),
        badcase_store=BadcaseStore(base_path / "badcases.jsonl"),
        model_router=model_router,
        event_sink=event_sink,
    )
    if settings.runtime == "native":
        return NativeWorkflowRuntime(**runtime_kwargs)

    from ananhu_agent.runtimes.langgraph.runtime import LangGraphWorkflowRuntime

    return LangGraphWorkflowRuntime(**runtime_kwargs)


def _default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索工伤法规、地方政策、办事指南",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            output_required_keys=["documents"],
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
            output_required_keys=["items", "assumptions"],
            handler=calculate_payment,
        )
    )
    return registry
