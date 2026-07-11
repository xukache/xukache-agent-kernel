from __future__ import annotations

from pathlib import Path
from typing import Any

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.capabilities.default_gateway import DefaultCapabilityGateway
from ananhu_agent.capabilities.registry import CapabilityDefinition, CapabilityRegistry
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.models.observable_gateway import ObservableModelGateway, TransientSanitizer
from ananhu_agent.models.model_router import ModelRouter
from ananhu_agent.infrastructure.knowledge.lexical_gateway import LexicalKnowledgeGateway
from ananhu_agent.ports.knowledge_gateway import EvidenceItem, KnowledgeGateway, KnowledgeQuery
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
from ananhu_agent.tools.payment_calculation import calculate_payment
from ananhu_agent.workflow.contracts import WorkflowRuntime


def create_default_runtime(
    base_path: Path,
    settings: RuntimeSettings | None = None,
    event_sink: RunEventSink | None = None,
    knowledge_gateway: KnowledgeGateway | None = None,
) -> WorkflowRuntime:
    """创建默认 WorkflowRuntime。

    默认装配 LangGraph Runtime，也可通过 RuntimeSettings 显式选择 Native；
    CLI/Eval 始终只依赖框架中立端口。
    """

    settings = settings or RuntimeSettings(runtime_dir=base_path)
    knowledge_gateway = knowledge_gateway or LexicalKnowledgeGateway(
        _default_policy_corpus_path()
    )
    model_router = ModelRouter(settings)
    trace_recorder = TraceRecorder(base_path / "traces.jsonl")
    direct_capability_trace = event_sink is None
    event_sink = event_sink or NoOpRunEventSink()
    capability_gateway = DefaultCapabilityGateway(
        _default_capability_registry(knowledge_gateway),
        event_sink=event_sink,
        trace_recorder=trace_recorder if direct_capability_trace else None,
    )
    intent_model_gateway = ObservableModelGateway(
        model_router.gateway_for("intent_fast"),
        events=event_sink,
        sanitizer=TransientSanitizer(),
    )
    runtime_kwargs = dict(
        intent_agent=IntentRouterAgent(
            intent_model_gateway,
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


def _default_capability_registry(
    knowledge_gateway: KnowledgeGateway,
) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityDefinition(
            name="knowledge.search",
            description="检索工伤法规、地方政策、办事指南",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=("PolicyRAGAgent",),
            required_input_keys=("query", "trusted_jurisdiction"),
            output_required_keys=(
                "evidences",
                "corpus_version",
                "applied_filters",
                "no_result_reason",
            ),
            output_validator=_validate_knowledge_output,
            handler=_search_knowledge_handler(knowledge_gateway),
        )
    )
    registry.register(
        CapabilityDefinition(
            name="payment.calculate",
            description="工伤待遇测算",
            risk_level="calculation",
            timeout_ms=3000,
            allowed_callers=("PaymentCalculationAgent",),
            required_input_keys=("disability_grade", "monthly_wage"),
            output_required_keys=("items", "assumptions"),
            output_validator=_validate_payment_output,
            handler=calculate_payment,
        )
    )
    return registry


def _search_knowledge_handler(
    knowledge_gateway: KnowledgeGateway,
):
    async def search_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
        """将能力输入显式转换为知识端口请求。"""

        result = await knowledge_gateway.search(
            KnowledgeQuery(
                query=payload["query"],
                tenant=payload.get("tenant", "default"),
                jurisdiction=payload["trusted_jurisdiction"],
                effective_at=payload.get("effective_at"),
                review_status="approved",
                audience_role=payload.get("audience_role", "public"),
                source_type=payload.get("source_type", "official"),
                document_version=payload.get("document_version"),
                top_k=payload.get("top_k", 3),
            )
        )
        return {
            "evidences": [
                item.model_dump(mode="json") for item in result.evidences
            ],
            "corpus_version": result.corpus_version,
            "applied_filters": result.applied_filters,
            "no_result_reason": result.no_result_reason,
        }

    return search_knowledge


def _default_policy_corpus_path() -> Path:
    """从 CLI 工作目录或包所在仓库根目录定位默认政策语料。"""

    relative_path = Path("data/policies/policy_corpus.v1.jsonl")
    if relative_path.exists():
        return relative_path
    return Path(__file__).resolve().parents[1] / relative_path


def _validate_knowledge_output(output: dict[str, Any]) -> None:
    if not isinstance(output["evidences"], list):
        raise TypeError("evidences must be a list")
    for evidence in output["evidences"]:
        EvidenceItem.model_validate(evidence)
    if not isinstance(output["corpus_version"], str):
        raise TypeError("corpus_version must be a string")
    if not isinstance(output["applied_filters"], dict):
        raise TypeError("applied_filters must be an object")
    if output["no_result_reason"] is not None and not isinstance(
        output["no_result_reason"], str
    ):
        raise TypeError("no_result_reason must be a string or null")


def _validate_payment_output(output: dict[str, Any]) -> None:
    if not isinstance(output["items"], list):
        raise TypeError("items must be a list")
    if not isinstance(output["assumptions"], dict):
        raise TypeError("assumptions must be an object")
