from __future__ import annotations


def score_case(answer: str, expected: list[str]) -> bool:
    """按 eval case 中声明的关键片段做最小可解释评分。"""

    return all(fragment in answer for fragment in expected)
