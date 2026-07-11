from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.infrastructure.knowledge.lexical_gateway import LexicalKnowledgeGateway
from ananhu_agent.ports.knowledge_gateway import KnowledgeQuery
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.runtimes.native.stages import NativeStageServices
from ananhu_agent.schemas import AgentContext, AgentMessage
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.workflow.contracts import WorkflowState


CORPUS_PATH = Path("data/policies/policy_corpus.v1.jsonl")


def _query(**overrides) -> KnowledgeQuery:
    values = {
        "query": "四川十级工伤 一次性伤残补助金",
        "tenant": "default",
        "jurisdiction": {"province": "四川省", "city": None},
        "effective_at": date(2026, 7, 11),
        "review_status": "approved",
        "audience_role": "public",
        "source_type": "official",
        "top_k": 3,
    }
    values.update(overrides)
    return KnowledgeQuery(**values)


def test_knowledge_gateway_returns_traceable_evidence_after_metadata_filter():
    gateway = LexicalKnowledgeGateway(CORPUS_PATH)

    result = asyncio.run(gateway.search(_query()))

    assert result.evidences
    evidence = result.evidences[0]
    assert evidence.document_id
    assert evidence.evidence_id
    assert evidence.title
    assert evidence.article
    assert evidence.content
    assert evidence.province in {"全国", "四川省"}
    assert evidence.review_status == "approved"
    assert evidence.document_version
    assert evidence.source_url.startswith("https://")
    assert evidence.retrieval_method == "lexical"
    assert evidence.lexical_score > 0
    assert len(evidence.evidence_hash) == 64
    assert result.corpus_version == "policy-corpus.v1"


def test_knowledge_gateway_excludes_local_policy_without_trusted_jurisdiction():
    gateway = LexicalKnowledgeGateway(CORPUS_PATH)

    result = asyncio.run(gateway.search(_query(jurisdiction={})))

    assert result.evidences == []
    assert result.no_result_reason == "no_trusted_jurisdiction_match"


def test_knowledge_gateway_does_not_accept_untrusted_model_jurisdiction():
    gateway = LexicalKnowledgeGateway(CORPUS_PATH)

    result = asyncio.run(
        gateway.search(
            _query(
                jurisdiction={"province": "四川省"},
                query="北京十级工伤 一次性伤残补助金",
            )
        )
    )

    assert result.evidences
    assert all(item.province in {"全国", "四川省"} for item in result.evidences)


def test_model_extracted_jurisdiction_cannot_overwrite_trusted_request_scope(tmp_path):
    ctx = AgentContext.new_for_query(
        session_id="session_1",
        turn_id=1,
        user_query="四川工伤待遇",
        province="四川省",
    )
    stages = NativeStageServices(
        ctx=ctx,
        intent_agent=None,
        domain_agent=None,
        payment_agent=None,
        policy_rag_agent=None,
        capability_gateway=None,
        trace_recorder=TraceRecorder(tmp_path / "trace.jsonl"),
        model_router=None,
    )
    stages._last_intent_message = AgentMessage(
        agent_name="IntentRouterAgent",
        status="success",
        content="识别",
        data={
            "intent": "payment_calculation",
            "confidence": 0.9,
            "slots": {"province": "北京市"},
            "missing_slots": [],
            "is_composite": False,
        },
    )

    stages.merge_facts(
        WorkflowState(
            run_id="run_1",
            request_id=ctx.request.request_id,
            session_id=ctx.request.session_id,
            case_facts={"user_query": ctx.request.user_query},
        )
    )

    assert ctx.request.province == "四川省"


def test_native_and_langgraph_can_share_one_knowledge_gateway(tmp_path):
    knowledge_gateway = LexicalKnowledgeGateway(CORPUS_PATH)
    native = create_default_runtime(
        tmp_path / "native",
        RuntimeSettings(runtime_dir=tmp_path / "native", runtime="native"),
        knowledge_gateway=knowledge_gateway,
    )
    langgraph = create_default_runtime(
        tmp_path / "langgraph",
        RuntimeSettings(runtime_dir=tmp_path / "langgraph", runtime="langgraph"),
        knowledge_gateway=knowledge_gateway,
    )

    assert native.capability_gateway.knowledge_gateway is knowledge_gateway
    assert langgraph.capability_gateway.knowledge_gateway is knowledge_gateway
