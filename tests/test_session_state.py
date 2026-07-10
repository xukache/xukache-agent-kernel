import asyncio
from uuid import uuid4

from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.storage.runtime_stores import SessionStateStore
from ananhu_agent.workflow.contracts import RunRequest


def test_session_state_persists_active_slots_between_turns(tmp_path):
    runtime = create_default_runtime(tmp_path)

    first = asyncio.run(runtime.invoke(_request("sess_1", 1, "四川十级工伤，月工资6000，大概能赔多少钱？")))
    second = asyncio.run(runtime.invoke(_request("sess_1", 2, "那九级呢？")))

    assert first.final_state.case_facts["province"] == "四川省"
    assert second.final_state.case_facts["province"] == "四川省"
    rows = SessionStateStore(tmp_path / "session_states.jsonl").read_all()
    assert rows[-1]["session_id"] == "sess_1"
    assert rows[-1]["active_slots"]["province"] == "四川省"


def _request(session_id: str, turn_id: int, query: str) -> RunRequest:
    return RunRequest(
        run_id=f"run_{uuid4().hex[:12]}",
        request_id=f"req_{uuid4().hex[:12]}",
        session_id=session_id,
        turn_id=turn_id,
        user_query=query,
        created_at="2026-07-10T00:00:00+08:00",
    )
