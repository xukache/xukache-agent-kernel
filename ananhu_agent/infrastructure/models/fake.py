from __future__ import annotations

import re
from typing import Any

from ananhu_agent.ports.model_gateway import ModelRequest, ModelResult, ModelUsage


class FakeModelGateway:
    """用于离线回归的确定性 ModelGateway 替身。"""

    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            output=_classify_and_extract(request.prompt),
            provider="fake",
            model="deterministic-intent",
            profile=request.profile,
            finish_reason="stop",
            usage=ModelUsage(usage_source="fake", reported=False),
            attempt=request.attempt,
        )


def _classify_and_extract(query: str) -> dict[str, Any]:
    query = _current_query_from_prompt(query)
    slots: dict[str, Any] = {}
    is_vague_recognition_question = "这个能不能算" in query
    if "四川" in query:
        slots["province"] = "四川省"
    if "十级" in query:
        slots["disability_grade"] = "十级"

    wage_match = re.search(r"月工资(\d+)", query)
    if wage_match:
        slots["monthly_wage"] = int(wage_match.group(1))

    if "赔多少钱" in query or "待遇" in query:
        intent = "payment_calculation"
    elif "劳动能力鉴定" in query:
        intent = "labor_capacity"
    elif "工伤" in query or "交通事故" in query or "政策" in query or "赔" in query or is_vague_recognition_question:
        intent = "work_injury_recognition"
    else:
        intent = "other"

    return {
        "intent": intent,
        "confidence": 0.4 if is_vague_recognition_question else 0.9,
        "slots": slots,
        "is_composite": False,
        "missing_slots": ["accident_type"] if is_vague_recognition_question else [],
    }


def _current_query_from_prompt(prompt: str) -> str:
    """只读取 Prompt 的当前问题分区，避免模板规则词污染离线意图分类。"""

    matched = re.search(r"\[Context\]\s*\n(.*?)\n\s*\[Output Schema\]", prompt, re.DOTALL)
    return matched.group(1).strip() if matched else prompt
