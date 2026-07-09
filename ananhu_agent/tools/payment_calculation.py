from __future__ import annotations

from typing import Any

GRADE_MONTHS = {"十级": 7, "九级": 9, "八级": 11, "七级": 13}


def calculate_payment(payload: dict[str, Any]) -> dict[str, Any]:
    """计算 MVP 支持的伤残等级一次性伤残补助金。

    当前只计算全国统一的按月数项目，地方差异和其他待遇项目由后续政策工具补充依据。
    """

    grade = payload["disability_grade"]
    monthly_wage = int(payload["monthly_wage"])
    months = GRADE_MONTHS[grade]
    amount = monthly_wage * months
    return {
        "items": [
            {
                "name": "一次性伤残补助金",
                "formula": f"{monthly_wage} * {months}",
                "amount": amount,
            }
        ],
        "assumptions": {
            "province": payload.get("province"),
            "disability_grade": grade,
            "monthly_wage": monthly_wage,
        },
        "disclaimer": "测算结果仅供咨询参考，以当地政策和经办机构核定为准。",
    }
