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

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> KnowledgeQuery:
        """将旧 PolicyRAGTool 输入转成新的知识端口请求。"""

        return cls(
            query=str(payload["query"]),
            tenant=str(payload.get("tenant", "default")),
            jurisdiction={
                "province": payload.get("province"),
                "city": payload.get("city"),
            }
            if "jurisdiction" not in payload
            else payload["jurisdiction"],
            effective_at=payload.get("effective_at"),
            review_status=payload.get("review_status", "approved"),
            audience_role=str(payload.get("audience_role", "public")),
            source_type=str(payload.get("source_type", "official")),
            document_version=payload.get("document_version"),
            top_k=int(payload.get("top_k", 3)),
        )


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

    def to_tool_payload(self) -> dict[str, Any]:
        """保留旧工具的 documents 形状，内部字段全部来自 EvidenceItem。"""

        return {
            "documents": [evidence.model_dump(mode="json") for evidence in self.evidences],
            "corpus_version": self.corpus_version,
            "applied_filters": self.applied_filters,
            "no_result_reason": self.no_result_reason,
        }


class KnowledgeGateway(ABC):
    """Runtime/应用依赖的框架中立知识检索端口。"""

    @abstractmethod
    async def search(self, request: KnowledgeQuery) -> KnowledgeSearchResult:
        """检索经过可信元数据过滤的政策证据。"""
