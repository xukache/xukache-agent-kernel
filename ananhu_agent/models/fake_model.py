from __future__ import annotations

import re
from typing import Any


class FakeModelClient:
    """测试用确定性模型客户端。

    MVP 当前不接真实模型 key，此客户端用可预测规则模拟意图识别与槽位抽取，
    让 Agent 编排链路能先稳定验证结构化协议。
    """

    def classify_and_extract(self, query: str) -> dict[str, Any]:
        slots: dict[str, Any] = {}
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
        elif "工伤" in query or "交通事故" in query:
            intent = "work_injury_recognition"
        else:
            intent = "other"

        return {
            "intent": intent,
            "confidence": 0.9,
            "slots": slots,
            "is_composite": False,
            "missing_slots": [],
        }
