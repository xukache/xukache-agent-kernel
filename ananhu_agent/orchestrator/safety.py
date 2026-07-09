from __future__ import annotations

from ananhu_agent.schemas import SafetyResult

ABSOLUTE_PHRASES = ("一定能", "肯定能", "保证", "必然认定")


class PolicySafetyGuard:
    """政务咨询安全守卫，拦截绝对化承诺。"""

    def check(self, answer: str) -> SafetyResult:
        warnings = [phrase for phrase in ABSOLUTE_PHRASES if phrase in answer]
        return SafetyResult(passed=not warnings, warnings=warnings)
