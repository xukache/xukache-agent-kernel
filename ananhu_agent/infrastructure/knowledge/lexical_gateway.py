from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from ananhu_agent.infrastructure.knowledge.corpus import PolicyDocument, load_policy_corpus
from ananhu_agent.ports.knowledge_gateway import (
    Citation,
    EvidenceItem,
    KnowledgeGateway,
    KnowledgeQuery,
    KnowledgeSearchResult,
)


class LexicalKnowledgeGateway(KnowledgeGateway):
    """先做可信元数据过滤，再执行可解释的关键词 lexical baseline。"""

    def __init__(self, corpus_path: Path) -> None:
        self.corpus_path = corpus_path
        self.corpus_documents = load_policy_corpus(corpus_path)
        self.corpus_version = self.corpus_documents[0].corpus_version

    async def search(self, request: KnowledgeQuery) -> KnowledgeSearchResult:
        return self._search(request)

    def _search(self, request: KnowledgeQuery) -> KnowledgeSearchResult:
        """执行可信元数据过滤和 lexical 召回。"""
        if not request.jurisdiction.get("province"):
            return KnowledgeSearchResult(
                query=request.query,
                corpus_version=self.corpus_version,
                applied_filters={
                    "tenant": request.tenant,
                    "jurisdiction": request.jurisdiction,
                    "effective_at": request.effective_at.isoformat()
                    if request.effective_at
                    else None,
                    "review_status": request.review_status,
                    "audience_role": request.audience_role,
                    "source_type": request.source_type,
                    "document_version": request.document_version,
                },
                no_result_reason="no_trusted_jurisdiction_match",
            )
        candidates = [
            document
            for document in self.corpus_documents
            if _matches_metadata(document, request)
        ]
        filters = {
            "tenant": request.tenant,
            "jurisdiction": request.jurisdiction,
            "effective_at": request.effective_at.isoformat() if request.effective_at else None,
            "review_status": request.review_status,
            "audience_role": request.audience_role,
            "source_type": request.source_type,
            "document_version": request.document_version,
        }
        if not candidates:
            return KnowledgeSearchResult(
                query=request.query,
                corpus_version=self.corpus_version,
                applied_filters=filters,
                no_result_reason="no_trusted_jurisdiction_match",
            )
        scored = [
            (score, document)
            for document in candidates
            if (score := _lexical_score(request.query, document)) > 0
        ]
        scored.sort(key=lambda item: (-item[0], item[1].document_id))
        evidences = [
            _to_evidence(document, score)
            for score, document in scored[: request.top_k]
        ]
        return KnowledgeSearchResult(
            query=request.query,
            corpus_version=self.corpus_version,
            applied_filters=filters,
            evidences=evidences,
            no_result_reason=None if evidences else "no_lexical_match",
        )


def _matches_metadata(document: PolicyDocument, request: KnowledgeQuery) -> bool:
    if document.tenant != request.tenant:
        return False
    if document.review_status != request.review_status:
        return False
    if document.source_type != request.source_type:
        return False
    if request.document_version and document.document_version != request.document_version:
        return False
    if request.audience_role not in document.audience_roles:
        return False

    effective_at = request.effective_at or date.today()
    if effective_at < document.effective_from:
        return False
    if document.effective_to is not None and effective_at >= document.effective_to:
        return False

    province = request.jurisdiction.get("province")
    city = request.jurisdiction.get("city")
    if document.province != "全国":
        if not province or province != document.province:
            return False
        if document.city and city and city != document.city:
            return False
        if document.city and not city:
            return False
    elif document.city and city and city != document.city:
        return False
    return True


def _lexical_score(query: str, document: PolicyDocument) -> float:
    normalized_query = _normalize(query)
    phrase_hits = sum(
        2.0
        for keyword in document.keywords
        if _normalize(keyword) and _normalize(keyword) in normalized_query
    )
    title_hits = sum(
        1.0
        for phrase in (document.title, document.article)
        if _normalize(phrase) and _normalize(phrase) in normalized_query
    )
    return phrase_hits + title_hits


def _to_evidence(document: PolicyDocument, score: float) -> EvidenceItem:
    evidence_id = f"{document.document_id}:{document.evidence_hash[:12]}"
    return EvidenceItem(
        evidence_id=evidence_id,
        document_id=document.document_id,
        id=document.document_id,
        title=document.title,
        article=document.article,
        content=document.content,
        tenant=document.tenant,
        province=document.province,
        city=document.city,
        effective_from=document.effective_from,
        effective_to=document.effective_to,
        review_status=document.review_status,
        audience_roles=document.audience_roles,
        source_type=document.source_type,
        document_version=document.document_version,
        source_url=document.source_url,
        corpus_version=document.corpus_version,
        evidence_hash=document.evidence_hash,
        lexical_score=score,
        citation=Citation(
            title=document.title,
            article=document.article,
            source_url=document.source_url,
            document_version=document.document_version,
            evidence_id=evidence_id,
            province=document.province,
            city=document.city,
        ),
    )


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()
