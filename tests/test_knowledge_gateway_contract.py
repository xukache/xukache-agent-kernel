from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from ananhu_agent.capabilities.contracts import CapabilityRequest, CapabilityStatus
from ananhu_agent.capabilities.default_gateway import DefaultCapabilityGateway
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.infrastructure.knowledge.lexical_gateway import LexicalKnowledgeGateway
from ananhu_agent.ports.knowledge_gateway import KnowledgeQuery
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.runtime import _default_capability_registry
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


def _execute_knowledge_capability(corpus_path: Path, **input_values):
    registry = _default_capability_registry(LexicalKnowledgeGateway(corpus_path))
    gateway = DefaultCapabilityGateway(registry)
    return asyncio.run(
        gateway.execute(
            CapabilityRequest(
                run_id="run_knowledge_contract",
                request_id="req_knowledge_contract",
                session_id="sess_knowledge_contract",
                capability_name="knowledge.search",
                caller="PolicyRAGAgent",
                input={
                    "query": "四川十级工伤 十级 待遇",
                    "trusted_jurisdiction": {"province": "四川省"},
                    **input_values,
                },
                node_id="execute",
                logical_call_id="knowledge_contract_call",
                attempt=1,
            )
        )
    )


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


def test_knowledge_gateway_does_not_expand_empty_scope_to_nationwide_policy():
    gateway = LexicalKnowledgeGateway(CORPUS_PATH)

    result = asyncio.run(
        gateway.search(
            _query(
                jurisdiction={},
                query="十级 一次性伤残补助金",
            )
        )
    )

    assert result.evidences == []
    assert result.no_result_reason == "no_trusted_jurisdiction_match"


def test_empty_trusted_scope_through_capability_gateway_is_safe_miss():
    result = _execute_knowledge_capability(
        CORPUS_PATH,
        query="十级 一次性伤残补助金",
        trusted_jurisdiction={},
    )

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["evidences"] == []
    assert result.output["no_result_reason"] == "no_trusted_jurisdiction_match"


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


def test_knowledge_gateway_excludes_expired_policy(tmp_path):
    corpus_path = tmp_path / "expired-policy.jsonl"
    corpus_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "document_id": "expired_policy",
                        "title": "已失效政策",
                        "article": "待遇章节",
                        "province": "四川省",
                        "keywords": ["十级", "待遇"],
                        "content": "这条政策已经失效。",
                        "effective_from": "2020-01-01",
                        "effective_to": "2025-01-01",
                        "review_status": "approved",
                        "audience_roles": ["public"],
                        "source_type": "official",
                        "document_version": "expired-v1",
                        "source_url": "https://example.com/expired",
                    }
                ),
                json.dumps(
                    {
                        "document_id": "current_policy",
                        "title": "当前政策",
                        "article": "待遇章节",
                        "province": "四川省",
                        "keywords": ["十级", "待遇"],
                        "content": "这条政策当前有效。",
                        "effective_from": "2025-01-01",
                        "review_status": "approved",
                        "audience_roles": ["public"],
                        "source_type": "official",
                        "document_version": "current-v1",
                        "source_url": "https://example.com/current",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = _execute_knowledge_capability(
        corpus_path,
        effective_at=date(2026, 7, 11),
    )

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["evidences"]
    assert {item["document_id"] for item in result.output["evidences"]} == {"current_policy"}


def test_knowledge_gateway_excludes_unreviewed_policy(tmp_path):
    corpus_path = tmp_path / "unreviewed-policy.jsonl"
    corpus_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "document_id": "draft_policy",
                        "title": "未审核政策",
                        "article": "待遇章节",
                        "province": "四川省",
                        "keywords": ["十级", "待遇"],
                        "content": "这条政策尚未审核。",
                        "effective_from": "2020-01-01",
                        "review_status": "draft",
                        "audience_roles": ["public"],
                        "source_type": "official",
                        "document_version": "draft-v1",
                        "source_url": "https://example.com/draft",
                    }
                ),
                json.dumps(
                    {
                        "document_id": "approved_policy",
                        "title": "已审核政策",
                        "article": "待遇章节",
                        "province": "四川省",
                        "keywords": ["十级", "待遇"],
                        "content": "这条政策已经审核。",
                        "effective_from": "2020-01-01",
                        "review_status": "approved",
                        "audience_roles": ["public"],
                        "source_type": "official",
                        "document_version": "approved-v1",
                        "source_url": "https://example.com/approved",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    result = _execute_knowledge_capability(
        corpus_path,
        query="四川十级工伤 十级 待遇",
    )

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["evidences"]
    assert {item["document_id"] for item in result.output["evidences"]} == {"approved_policy"}


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

    assert native.capability_gateway.registry.get("knowledge.search") is not None
    assert langgraph.capability_gateway.registry.get("knowledge.search") is not None
    assert native.capability_gateway is not langgraph.capability_gateway
    assert native.capability_gateway.registry.names() == (
        "knowledge.search",
        "payment.calculate",
    )
    assert langgraph.capability_gateway.registry.names() == (
        "knowledge.search",
        "payment.calculate",
    )


def test_knowledge_search_capability_returns_evidences_directly():
    result = _execute_knowledge_capability(
        CORPUS_PATH,
        query="四川十级工伤 一次性伤残补助金",
        province="北京市",
        top_k=3,
    )

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["evidences"]
    assert all(
        item["province"] in {"全国", "四川省"}
        for item in result.output["evidences"]
    )
    assert "documents" not in result.output
