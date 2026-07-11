from __future__ import annotations

from pathlib import Path

from ananhu_agent.evaluation.rag import RAGEvalRunner
from ananhu_agent.infrastructure.knowledge.lexical_gateway import LexicalKnowledgeGateway


def test_rag_eval_reports_recall_mrr_and_citation_support(tmp_path):
    gateway = LexicalKnowledgeGateway(Path("data/policies/policy_corpus.v1.jsonl"))
    report = RAGEvalRunner(gateway).run(
        Path("data/eval/rag_cases.jsonl"),
        artifact_path=tmp_path / "rag-eval.json",
    )

    assert report["total"] == 3
    assert report["recall_at_k"] == 1.0
    assert report["mrr"] == 1.0
    assert report["citation_support_rate"] == 1.0
    assert report["trusted_filter_rate"] == 1.0
    assert (tmp_path / "rag-eval.json").exists()


def test_rag_eval_keeps_no_result_case_as_a_safe_miss(tmp_path):
    gateway = LexicalKnowledgeGateway(Path("data/policies/policy_corpus.v1.jsonl"))
    report = RAGEvalRunner(gateway).run(
        Path("data/eval/rag_cases_no_result.jsonl"),
        artifact_path=tmp_path / "rag-eval-no-result.json",
    )

    assert report["total"] == 1
    assert report["no_result_rate"] == 1.0
    assert report["fabrication_allowed"] is False
