from __future__ import annotations

from typing import Any

from ananhu_agent.schemas import AgentContext


def build_final_answer(ctx: AgentContext) -> str:
    """将 Agent 输出和工具结果聚合为面向用户的最终咨询答案。"""

    documents = _collect_policy_documents(ctx)
    payment_result = _collect_payment_result(ctx)
    if not documents:
        return _build_conservative_answer(payment_result)

    lines = ["结论：需结合事实、地区政策和正式材料判断，以下为咨询参考。"]
    lines.extend(_build_payment_lines(payment_result))
    lines.extend(_build_citation_lines(documents))
    lines.extend(_build_guidance_lines(payment_result))
    lines.append("风险提示：具体结论以经办机构和正式材料为准。")
    return "\n".join(lines)


def _build_conservative_answer(payment_result: dict[str, Any] | None) -> str:
    lines = [
        "结论：当前没有检索到可引用的结构化政策依据，不能给出确定结论。",
        "依据：暂无可引用的结构化政策依据。",
    ]
    if payment_result:
        lines.append("测算：因缺少可引用政策依据，金额仅能作为公式演示，不能作为待遇承诺。")
    lines.append("建议：请补充地区、工伤认定材料、劳动能力鉴定结论和经办机构口径后再判断。")
    lines.append("风险提示：具体结论以经办机构和正式材料为准。")
    return "\n".join(lines)


def _collect_policy_documents(ctx: AgentContext) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for result in ctx.tool_results:
        if result.tool_name == "PolicyRAGTool" and result.tool_status == "success":
            documents.extend(result.output.get("documents", []))
    return documents


def _collect_payment_result(ctx: AgentContext) -> dict[str, Any] | None:
    for result in ctx.tool_results:
        if result.tool_name == "PaymentCalculationTool" and result.tool_status == "success":
            return result.output
    return None


def _build_payment_lines(payment_result: dict[str, Any] | None) -> list[str]:
    if not payment_result:
        return []

    lines = ["测算："]
    for item in payment_result.get("items", []):
        lines.append(f"- {item['name']}：{item['amount']} 元，公式：{item['formula']}")
    return lines


def _build_citation_lines(documents: list[dict[str, Any]]) -> list[str]:
    if not documents:
        return ["依据：暂无可引用的结构化政策依据。"]

    lines = ["依据："]
    for index, document in enumerate(documents, start=1):
        citation = document["citation"]
        lines.append(f"[{index}] {citation['title']} {citation['article']}：{document['content']}")
    return lines


def _build_guidance_lines(payment_result: dict[str, Any] | None) -> list[str]:
    lines = ["适用条件：以上判断需满足事实真实、责任划分明确、地区政策适用一致。"]
    if payment_result:
        assumptions = payment_result.get("assumptions", {})
        assumption_text = "，".join(
            f"{key}={value}" for key, value in assumptions.items() if value is not None
        )
        if assumption_text:
            lines.append(f"测算假设：{assumption_text}。")
    else:
        lines.append("材料建议：保留事故认定书、劳动关系证明、就医材料和单位申报材料。")
    return lines
