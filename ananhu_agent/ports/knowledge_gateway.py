from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


KNOWLEDGE_SCHEMA_VERSION = "knowledge.v1"


class KnowledgeQuery(BaseModel):
    """知识检索请求，只接受项目确认后的可信元数据。"""

    schema_version: Literal["knowledge.v1"] = KNOWLEDGE_SCHEMA_VERSION
    query: str = Field(min_length=1)
    tenant: str = "default"
    jurisdiction: dict[str, str | None] = Field(default_factory=dict)
    effective_at: date | None = None
    review_status: Literal["approved"] = "approved"
    audience_role: str = "public"
    source_type: str = "official"
    document_version: str | None = None
    top_k: int = Field(default=3, ge=1, le=20)

class Citation(BaseModel):
    """答案引用和证据溯源使用的稳定最小投影。"""

    title: str
    article: str
    source_url: str
    document_version: str
    evidence_id: str
    province: str
    city: str


class EvidenceItem(BaseModel):
    """可回指政策原文的检索证据。"""

    schema_version: Literal["knowledge.v1"] = KNOWLEDGE_SCHEMA_VERSION
    evidence_id: str
    document_id: str
    id: str
    title: str
    article: str
    content: str
    tenant: str
    province: str
    city: str
    effective_from: date
    effective_to: date | None = None
    review_status: str
    audience_roles: list[str]
    source_type: str
    document_version: str
    source_url: str
    corpus_version: str
    evidence_hash: str
    retrieval_method: Literal["lexical"] = "lexical"
    lexical_score: float
    fusion_score: float | None = None
    rerank_score: float | None = None
    citation: Citation


class KnowledgeSearchResult(BaseModel):
    """KnowledgeGateway 的结构化返回，不把无结果伪装成自然语言证据。"""

    schema_version: Literal["knowledge.v1"] = KNOWLEDGE_SCHEMA_VERSION
    query: str
    corpus_version: str
    applied_filters: dict[str, Any]
    evidences: list[EvidenceItem] = Field(default_factory=list)
    no_result_reason: str | None = None


class KnowledgeGateway(ABC):
    """Runtime/应用依赖的框架中立知识检索端口。"""

    @abstractmethod
    async def search(self, request: KnowledgeQuery) -> KnowledgeSearchResult:
        """检索经过可信元数据过滤的政策证据。"""
