from __future__ import annotations

from ananhu_agent.schemas import SafetyResult

ABSOLUTE_PHRASES = ("一定能", "肯定能", "保证", "必然认定")
MEDICAL_GRADE_PHRASES = ("肯定可以评为", "一定可以评为", "保证评为")
AGENCY_DECISION_PHRASES = ("不用经办机构", "无需经办机构", "替代经办机构")
PRECISE_AMOUNT_PHRASES = ("一定赔", "肯定赔", "保证赔")


class PolicySafetyGuard:
    """政务咨询安全守卫，返回稳定 issue code 而不是原始敏感短语。"""

    def check(self, answer: str) -> SafetyResult:
        warnings: list[str] = []
        if any(phrase in answer for phrase in ABSOLUTE_PHRASES):
            warnings.append("absolute_commitment")
        if ("伤残" in answer or "劳动能力" in answer) and any(
            phrase in answer for phrase in MEDICAL_GRADE_PHRASES
        ):
            warnings.append("medical_grade_commitment")
        if any(phrase in answer for phrase in AGENCY_DECISION_PHRASES):
            warnings.append("agency_decision_substitution")
        if any(phrase in answer for phrase in PRECISE_AMOUNT_PHRASES):
            warnings.append("precise_amount_commitment")
        return SafetyResult(passed=not warnings, warnings=warnings)
