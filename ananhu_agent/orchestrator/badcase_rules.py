from __future__ import annotations

from ananhu_agent.schemas import AgentContext

LOW_INTENT_CONFIDENCE_THRESHOLD = 0.5


def detect_badcase_issues(ctx: AgentContext) -> list[str]:
    """基于单轮运行结果识别系统自动 badcase 候选原因。"""
    issues: list[str] = []

    if ctx.intent_result and ctx.intent_result.confidence < LOW_INTENT_CONFIDENCE_THRESHOLD:
        issues.append("low_intent_confidence")

    if _policy_rag_returned_no_result(ctx):
        issues.append("rag_no_result")

    if ctx.verification_result:
        for issue in ctx.verification_result.issues:
            if issue == "missing_citation":
                issues.append("missing_citation")

    if any(result.tool_status == "failed" for result in ctx.tool_results):
        issues.append("tool_failed")

    if ctx.safety_result and not ctx.safety_result.passed:
        issues.append("unsafe_answer")

    if not (ctx.final_answer or "").strip():
        issues.append("empty_answer")

    return _dedupe_preserve_order(issues)


def _policy_rag_returned_no_result(ctx: AgentContext) -> bool:
    rag_results = [result for result in ctx.tool_results if result.tool_name == "PolicyRAGTool"]
    return any(result.tool_status == "success" and not result.output.get("documents") for result in rag_results)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped
