from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from ananhu_agent.ports.knowledge_gateway import KnowledgeGateway, KnowledgeQuery


class RAGEvalRunner:
    """只评估检索机制，不把答案生成通过率冒充 RAG 质量。"""

    def __init__(self, gateway: KnowledgeGateway) -> None:
        self.gateway = gateway

    def run(self, cases_path: Path, artifact_path: Path | None = None) -> dict[str, Any]:
        rows = [
            json.loads(line)
            for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        case_results: list[dict[str, Any]] = []
        hits = 0
        reciprocal_rank = 0.0
        citation_supported = 0
        trusted_filtered = 0
        no_results = 0

        for case in rows:
            result = asyncio.run(
                self.gateway.search(
                    KnowledgeQuery(
                        query=case["query"],
                        jurisdiction=case.get("jurisdiction", {}),
                        top_k=case.get("top_k", 3),
                    )
                )
            )
            evidence_ids = [evidence.document_id for evidence in result.evidences]
            expected_ids = case.get("expected_document_ids", [])
            hit = bool(expected_ids) and all(expected in evidence_ids for expected in expected_ids)
            if hit:
                hits += 1
                ranks = [evidence_ids.index(expected) + 1 for expected in expected_ids]
                reciprocal_rank += 1 / min(ranks)
                citation_supported += int(
                    all(
                        evidence.citation.evidence_id == evidence.evidence_id
                        for evidence in result.evidences
                    )
                )
            if not expected_ids and not result.evidences:
                no_results += 1
            trusted_filtered += int(
                all(
                    evidence.province == "全国"
                    or evidence.province == case.get("jurisdiction", {}).get("province")
                    for evidence in result.evidences
                )
            )
            case_results.append(
                {
                    "id": case["id"],
                    "expected_document_ids": expected_ids,
                    "retrieved_document_ids": evidence_ids,
                    "no_result_reason": result.no_result_reason,
                }
            )

        total = len(rows)
        report = {
            "schema_version": "rag-eval.v1",
            "total": total,
            "recall_at_k": _rate(hits, sum(bool(case.get("expected_document_ids")) for case in rows)),
            "mrr": reciprocal_rank / hits if hits else 0.0,
            "citation_support_rate": _rate(citation_supported, hits),
            "trusted_filter_rate": _rate(trusted_filtered, total),
            "no_result_rate": _rate(no_results, sum(not case.get("expected_document_ids") for case in rows)),
            "fabrication_allowed": False,
            "cases": case_results,
        }
        if artifact_path is not None:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return report


def _rate(passed: int, total: int) -> float | None:
    if total == 0:
        return None
    return passed / total
