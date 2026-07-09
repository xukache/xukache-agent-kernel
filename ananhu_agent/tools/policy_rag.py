from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def search_policy(payload: dict[str, Any]) -> dict[str, Any]:
    """基于本地 fixture 的确定性政策检索。

    MVP 阶段先用关键词和地区过滤保证可回放；后续替换为向量检索时仍保持相同输出协议。
    """

    query = payload["query"]
    province = payload.get("province")
    top_k = int(payload.get("top_k", 3))
    fixture_path = Path(payload.get("fixture_path", "data/policies/policy_fixtures.jsonl"))

    rows = [
        json.loads(line)
        for line in fixture_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        region_match = row["province"] in ("全国", province, None, "")
        keyword_score = sum(1 for keyword in row["keywords"] if keyword in query)
        if region_match and keyword_score > 0:
            scored.append((keyword_score, row))

    documents = [
        {
            "id": row["id"],
            "content": row["content"],
            "citation": {"title": row["title"], "article": row["article"]},
        }
        for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
    ]
    return {"documents": documents}
