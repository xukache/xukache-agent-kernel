from ananhu_agent.context.slot_rules import merge_slots
from ananhu_agent.orchestrator.rules import revise_intent
from ananhu_agent.schemas import IntentResult


def test_payment_keyword_overrides_low_value_intent():
    result = IntentResult(intent="policy_consultation", confidence=0.7)
    revised = revise_intent("四川十级工伤大概能赔多少钱？", result)

    assert revised.intent == "payment_calculation"


def test_low_confidence_with_missing_slots_asks_clarification():
    result = IntentResult(
        intent="work_injury_recognition",
        confidence=0.4,
        missing_slots=["accident_type"],
    )
    revised = revise_intent("这个能不能算？", result)

    assert revised.ask_clarification == "请补充事故场景、发生时间、地区和责任划分。"


def test_current_region_overrides_history_region():
    merged, metadata = merge_slots(
        history={"province": "四川省", "city": "成都市"},
        current={"province": "辽宁省", "city": "丹东市"},
    )

    assert merged["province"] == "辽宁省"
    assert metadata["region_overridden"] is True


def test_merge_slots_normalizes_province_short_name():
    merged, metadata = merge_slots(history={}, current={"province": "四川"})

    assert merged["province"] == "四川省"
    assert metadata["region_inherited"] is False
