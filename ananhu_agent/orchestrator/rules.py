from __future__ import annotations

from ananhu_agent.schemas import IntentResult

PAYMENT_KEYWORDS = ("赔多少钱", "待遇", "一次性伤残补助金", "医疗补助金")
RECOGNITION_KEYWORDS = ("算不算工伤", "能不能认定", "上下班途中", "非本人主要责任")
LABOR_CAPACITY_KEYWORDS = ("劳动能力鉴定", "伤残等级", "鉴定材料", "复查鉴定")

LOW_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_CLARIFICATION = "请补充事故场景、发生时间、地区和责任划分。"


def revise_intent(user_query: str, result: IntentResult) -> IntentResult:
    """基于确定性关键词和置信度规则修正模型初判意图。"""
    data = result.model_copy(deep=True)

    # 强关键词优先于低价值泛化意图，避免待遇测算等明确问题被路由到普通咨询。
    if any(keyword in user_query for keyword in PAYMENT_KEYWORDS):
        data.intent = "payment_calculation"
    elif any(keyword in user_query for keyword in RECOGNITION_KEYWORDS):
        data.intent = "work_injury_recognition"
    elif any(keyword in user_query for keyword in LABOR_CAPACITY_KEYWORDS):
        data.intent = "labor_capacity"

    if data.confidence < LOW_CONFIDENCE_THRESHOLD and data.missing_slots:
        data.ask_clarification = DEFAULT_CLARIFICATION

    return data
