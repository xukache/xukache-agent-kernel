from __future__ import annotations

from typing import Any

from ananhu_agent.workflow.contracts import WorkflowState


def score_case(answer: str, expected: list[str]) -> bool:
    """按 eval case 中声明的关键片段做最小可解释评分。"""

    return all(fragment in answer for fragment in expected)


def score_intent(state: WorkflowState, expected_intent: str) -> bool:
    """评估最终修正后的意图是否符合 eval case 期望。"""

    return bool(state.intent_result and state.intent_result.get("intent") == expected_intent)


def score_slots(state: WorkflowState, expected_slots: dict[str, Any]) -> bool:
    """评估期望槽位是否都被抽取并合并到当前 active slots。"""

    return all(
        state.case_facts.get(key) == value
        for key, value in expected_slots.items()
    )


def score_citations(state: WorkflowState, expected_citations: list[str]) -> bool:
    """评估期望法规来源是否出现在 RAG 工具返回的引用标题中。"""

    citation_titles = [
        item["document"]["citation"].get("title", "")
        for item in state.evidence
    ]
    return all(
        any(expected in title for title in citation_titles) for expected in expected_citations
    )


def score_evidence_support(evidence_ids: list[str], expected_ids: list[str]) -> bool:
    """评估检索结果是否包含全部标注证据，供 RAG 专项 eval 使用。"""

    return all(expected in evidence_ids for expected in expected_ids)


def score_tool_success(state: WorkflowState) -> bool:
    """评估本轮实际发生的工具调用是否全部成功。"""

    return bool(state.capability_results) and all(
        result.get("tool_status") == "success" for result in state.capability_results
    )


def score_safety(state: WorkflowState) -> bool:
    """评估最终答案是否通过政务安全守卫。"""

    return bool(state.safety_result and state.safety_result.get("passed"))
