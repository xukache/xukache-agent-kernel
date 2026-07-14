"""RD 场景注册表的确定性测试。"""

from tests.real_dialogue.scenarios import REAL_DIALOGUE_SCENARIOS


def test_all_rd_scenarios_have_unique_ids_and_fixed_inputs() -> None:
    ids = [scenario.test_id for scenario in REAL_DIALOGUE_SCENARIOS]

    assert ids == [f"RD-{index:03d}" for index in range(1, 13)]
    assert len(set(ids)) == 12
    assert all(scenario.raw_dialogue_input for scenario in REAL_DIALOGUE_SCENARIOS)
    assert all(scenario.module for scenario in REAL_DIALOGUE_SCENARIOS)


def test_each_scenario_declares_required_evidence_fields() -> None:
    for scenario in REAL_DIALOGUE_SCENARIOS:
        assert scenario.required_evidence
        assert scenario.blocking_conditions
