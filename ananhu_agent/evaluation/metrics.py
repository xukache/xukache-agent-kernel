from __future__ import annotations

from typing import Any

from ananhu_agent.schemas import AgentContext


def score_case(answer: str, expected: list[str]) -> bool:
    """按 eval case 中声明的关键片段做最小可解释评分。"""

    return all(fragment in answer for fragment in expected)


def score_intent(ctx: AgentContext, expected_intent: str) -> bool:
    """评估最终修正后的意图是否符合 eval case 期望。"""

    return bool(ctx.intent_result and ctx.intent_result.intent == expected_intent)


def score_slots(ctx: AgentContext, expected_slots: dict[str, Any]) -> bool:
    """评估期望槽位是否都被抽取并合并到当前 active slots。"""

    return all(
        ctx.conversation.active_slots.get(key) == value
        for key, value in expected_slots.items()
    )


def score_citations(ctx: AgentContext, expected_citations: list[str]) -> bool:
    """评估期望法规来源是否出现在 RAG 工具返回的引用标题中。"""

    citation_titles = [
        document["citation"].get("title", "")
        for result in ctx.tool_results
        if result.tool_name == "PolicyRAGTool"
        for document in result.output.get("documents", [])
    ]
    return all(
        any(expected in title for title in citation_titles) for expected in expected_citations
    )


def score_tool_success(ctx: AgentContext) -> bool:
    """评估本轮实际发生的工具调用是否全部成功。"""

    return bool(ctx.tool_results) and all(
        result.tool_status == "success" for result in ctx.tool_results
    )


def score_safety(ctx: AgentContext) -> bool:
    """评估最终答案是否通过政务安全守卫。"""

    return bool(ctx.safety_result and ctx.safety_result.passed)
