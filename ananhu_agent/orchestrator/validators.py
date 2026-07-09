from __future__ import annotations

from typing import Any

from ananhu_agent.schemas import VerificationResult


class AnswerValidator:
    """最终答案结构校验，防止无依据内容进入回复。"""

    def validate(self, answer: str, citations: list[dict[str, Any]]) -> VerificationResult:
        issues: list[str] = []
        if not citations:
            issues.append("missing_citation")
        if "风险提示：" not in answer:
            issues.append("missing_risk_note")
        return VerificationResult(passed=not issues, issues=issues)
