from __future__ import annotations

from typing import Any


_PROVINCES = {
    "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建",
    "江西", "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州",
    "云南", "陕西", "甘肃", "青海", "台湾",
}
_PROVINCE_ALIASES = {
    "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
    "内蒙古": "内蒙古自治区", "广西": "广西壮族自治区", "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
    "香港": "香港特别行政区", "澳门": "澳门特别行政区",
}


def merge_slots(
    history: dict[str, Any],
    current: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, bool]]:
    """合并历史槽位与当前轮槽位，并标记地区继承/覆盖证据。"""
    current_values = {key: value for key, value in current.items() if value not in (None, "")}
    if isinstance(current_values.get("province"), str):
        current_values["province"] = _normalize_province(current_values["province"])
    merged = {**history, **current_values}

    metadata = {
        "region_inherited": False,
        "region_overridden": False,
    }

    # 地区是政策适用边界：当前轮未给出时允许继承，明确给出时必须覆盖历史地区。
    if "province" not in current_values and "province" in history:
        metadata["region_inherited"] = True
    if (
        current_values.get("province")
        and history.get("province")
        and current_values["province"] != history["province"]
    ):
        metadata["region_overridden"] = True

    return merged, metadata


def _normalize_province(value: str) -> str:
    """将模型常见省级简称归一为政策元数据使用的行政区全称。"""

    name = value.strip()
    if name in _PROVINCES:
        return f"{name}省"
    return _PROVINCE_ALIASES.get(name, name)
