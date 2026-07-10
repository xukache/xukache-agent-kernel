from __future__ import annotations

from ananhu_agent.workflow.contracts import WorkflowState

LOW_INTENT_CONFIDENCE_THRESHOLD = 0.5


def detect_badcase_issues(state: WorkflowState) -> list[str]:
    """基于单轮运行结果识别系统自动 badcase 候选原因。"""
    issues: list[str] = []

    if (
        state.intent_result
        and state.intent_result.get("confidence", 1.0) < LOW_INTENT_CONFIDENCE_THRESHOLD
    ):
        issues.append("low_intent_confidence")

    if _policy_rag_returned_no_result(state):
        issues.append("rag_no_result")

    if state.verification_result:
        for issue in state.verification_result.get("issues", []):
            if issue == "missing_citation":
                issues.append("missing_citation")

    if any(result.get("tool_status") == "failed" for result in state.capability_results):
        issues.append("tool_failed")

    if state.safety_result and not state.safety_result.get("passed", True):
        issues.append("unsafe_answer")

    if not (state.final_answer or "").strip():
        issues.append("empty_answer")

    return _dedupe_preserve_order(issues)


def _policy_rag_returned_no_result(state: WorkflowState) -> bool:
    rag_results = [
        result for result in state.capability_results if result.get("tool_name") == "PolicyRAGTool"
    ]
    return any(
        result.get("tool_status") == "success" and not result.get("output", {}).get("documents")
        for result in rag_results
    )


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped
