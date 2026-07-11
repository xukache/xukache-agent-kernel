from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


CORPUS_SCHEMA_VERSION = "policy-document.v1"
CORPUS_VERSION = "policy-corpus.v1"


class PolicyDocument(BaseModel):
    """单条政策语料及其治理元数据。"""

    schema_version: str = CORPUS_SCHEMA_VERSION
    document_id: str
    title: str
    article: str
    province: str
    city: str = ""
    keywords: list[str] = Field(min_length=1)
    content: str
    tenant: str = "default"
    effective_from: date
    effective_to: date | None = None
    review_status: str
    audience_roles: list[str] = Field(min_length=1)
    source_type: str
    document_version: str
    source_url: str
    corpus_version: str = CORPUS_VERSION
    evidence_hash: str

    @field_validator("review_status")
    @classmethod
    def require_known_review_status(cls, value: str) -> str:
        if value not in {"approved", "draft", "rejected"}:
            raise ValueError(f"unsupported review status: {value}")
        return value

    @field_validator("source_url")
    @classmethod
    def require_https_source(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("policy source_url must use https")
        return value

    @field_validator("effective_to")
    @classmethod
    def require_valid_effective_range(
        cls,
        value: date | None,
        info,
    ) -> date | None:
        effective_from = info.data.get("effective_from")
        if value is not None and effective_from is not None and value <= effective_from:
            raise ValueError("effective_to must be after effective_from")
        return value


def load_policy_corpus(path: Path) -> list[PolicyDocument]:
    """加载并补齐可验证的证据 hash，拒绝重复文档 ID。"""

    documents: list[PolicyDocument] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        raw.setdefault("document_id", raw.get("id"))
        raw.setdefault("schema_version", CORPUS_SCHEMA_VERSION)
        raw.setdefault("tenant", "default")
        raw.setdefault("city", "")
        raw.setdefault("effective_from", "1970-01-01")
        raw.setdefault("review_status", "approved")
        raw.setdefault("audience_roles", ["public", "agent"])
        raw.setdefault("source_type", "official")
        raw.setdefault("document_version", "legacy-fixture")
        raw.setdefault(
            "source_url",
            f"https://example.invalid/policy-fixtures/{raw.get('document_id')}",
        )
        raw.setdefault("corpus_version", CORPUS_VERSION)
        raw.setdefault("evidence_hash", _document_hash(raw))
        document = PolicyDocument.model_validate(raw)
        if document.document_id in seen_ids:
            raise ValueError(f"duplicate policy document id at line {line_number}: {document.document_id}")
        seen_ids.add(document.document_id)
        documents.append(document)
    if not documents:
        raise ValueError(f"policy corpus is empty: {path}")
    return documents


def _document_hash(raw: dict[str, Any]) -> str:
    """只对政策正文和稳定文档标识做 hash，避免时间和排序影响证据 ID。"""

    canonical = json.dumps(
        {
            "document_id": raw.get("document_id", raw.get("id", "")),
            "title": raw.get("title", ""),
            "article": raw.get("article", ""),
            "content": raw.get("content", ""),
            "document_version": raw.get("document_version", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
