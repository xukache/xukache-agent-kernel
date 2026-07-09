from __future__ import annotations

from typing import Any


def format_citations(payload: dict[str, Any]) -> dict[str, Any]:
    """将工具返回的 citation 按稳定顺序格式化为最终答案可引用结构。"""

    citations = []
    for index, document in enumerate(payload["documents"], start=1):
        citation = document["citation"]
        citations.append(
            {
                "index": index,
                "label": f"[{index}] {citation['title']} {citation['article']}",
                "title": citation["title"],
                "article": citation["article"],
            }
        )
    return {"citations": citations}
