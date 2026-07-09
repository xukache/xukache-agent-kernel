from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator
from ananhu_agent.storage.runtime_stores import SessionStateStore


def test_session_state_persists_active_slots_between_turns(tmp_path):
    orchestrator = create_default_orchestrator(tmp_path)

    first = orchestrator.ask("sess_1", 1, "四川十级工伤，月工资6000，大概能赔多少钱？")
    second = orchestrator.ask("sess_1", 2, "那九级呢？")

    assert first.conversation.active_slots["province"] == "四川省"
    assert second.conversation.active_slots["province"] == "四川省"
    assert second.request.province == "四川省"
    rows = SessionStateStore(tmp_path / "session_states.jsonl").read_all()
    assert rows[-1]["session_id"] == "sess_1"
    assert rows[-1]["active_slots"]["province"] == "四川省"
