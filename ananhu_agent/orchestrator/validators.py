from __future__ import annotations

from typing import Any

from ananhu_agent.schemas import VerificationResult


class AnswerValidator:
    """最终答案结构校验，防止无依据内容进入回复。"""

    def validate(
        self,
        answer: str,
        citations: list[dict[str, Any]],
        expected_region: dict[str, str | None] | None = None,
    ) -> VerificationResult:
        issues: list[str] = []
        if not citations:
            issues.append("missing_citation")
        if "风险提示：" not in answer:
            issues.append("missing_risk_note")
        if expected_region and self._has_region_mismatch(citations, expected_region):
            issues.append("region_mismatch")
        return VerificationResult(passed=not issues, issues=issues)

    @staticmethod
    def _has_region_mismatch(
        citations: list[dict[str, Any]],
        expected_region: dict[str, str | None],
    ) -> bool:
        expected_province = expected_region.get("province")
        if not expected_province:
            return False

        citation_provinces = {
            citation.get("province")
            for citation in citations
            if citation.get("province") not in (None, "", "全国")
        }
        return bool(citation_provinces and expected_province not in citation_provinces)
