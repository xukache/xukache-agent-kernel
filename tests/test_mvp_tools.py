from pathlib import Path

from ananhu_agent.tools.formatters import format_citations
from ananhu_agent.tools.payment_calculation import calculate_payment
from ananhu_agent.tools.policy_rag import search_policy


def test_policy_rag_returns_grounded_fixture_documents():
    result = search_policy(
        {
            "query": "上下班途中交通事故能不能认定工伤",
            "province": "四川省",
            "city": "成都市",
            "top_k": 3,
            "fixture_path": Path("data/policies/policy_fixtures.jsonl"),
        }
    )

    assert result["documents"]
    assert result["documents"][0]["citation"]["title"] == "工伤保险条例"


def test_payment_calculation_returns_assumptions_and_items():
    result = calculate_payment(
        {
            "province": "四川省",
            "disability_grade": "十级",
            "monthly_wage": 6000,
        }
    )

    assert result["items"][0]["name"] == "一次性伤残补助金"
    assert result["items"][0]["amount"] == 42000
    assert "以当地政策和经办机构核定为准" in result["disclaimer"]


def test_citation_formatter_outputs_ordered_citations():
    citations = format_citations(
        {
            "documents": [
                {"citation": {"title": "工伤保险条例", "article": "第十四条"}},
                {"citation": {"title": "四川省工伤保险条例实施办法", "article": "待遇章节"}},
            ]
        }
    )

    assert citations["citations"][0]["label"] == "[1] 工伤保险条例 第十四条"
