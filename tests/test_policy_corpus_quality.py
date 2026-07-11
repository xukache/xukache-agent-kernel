from __future__ import annotations

from datetime import date
from pathlib import Path

from ananhu_agent.infrastructure.knowledge.corpus import load_policy_corpus


def test_policy_corpus_has_reviewed_traceable_metadata():
    documents = load_policy_corpus(Path("data/policies/policy_corpus.v1.jsonl"))

    assert len(documents) >= 3
    assert len({document.document_id for document in documents}) == len(documents)

    for document in documents:
        assert document.tenant == "default"
        assert document.title
        assert document.article
        assert document.content
        assert document.province
        assert document.review_status == "approved"
        assert document.document_version
        assert document.source_type == "official"
        assert document.source_url.startswith("https://")
        assert document.effective_from <= date(2026, 7, 11)
        assert document.evidence_hash
        assert document.corpus_version == "policy-corpus.v1"
