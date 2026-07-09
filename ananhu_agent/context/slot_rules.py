from __future__ import annotations

from typing import Any


def merge_slots(
    history: dict[str, Any],
    current: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, bool]]:
    """合并历史槽位与当前轮槽位，并标记地区继承/覆盖证据。"""
    current_values = {key: value for key, value in current.items() if value not in (None, "")}
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
