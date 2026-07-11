from ananhu_agent.schemas import BadcaseRecord
from ananhu_agent.storage.runtime_stores import BadcaseStore


def test_badcase_store_preserves_existing_jsonl_contract(tmp_path):
    store = BadcaseStore(tmp_path / "badcases.jsonl")

    store.append(BadcaseRecord(
        id="badcase_1", request_id="req_1", session_id="sess_1", turn_id=1,
        query="四川十级工伤", predicted_intent="payment_calculation",
        issue_type="region_policy_mismatch", agent_route=["PaymentCalculationAgent"],
        capability_calls=["payment.calculate"], actual_answer="旧答案",
        expected_answer="应核对地方政策", correction_note="地区政策不匹配",
        added_to_eval=False, fixed=False, created_at="2026-07-10T00:00:00+08:00",
    ))

    assert store.read_all() == [{
        "id": "badcase_1", "request_id": "req_1", "session_id": "sess_1", "turn_id": 1,
        "query": "四川十级工伤", "predicted_intent": "payment_calculation",
        "issue_type": "region_policy_mismatch", "agent_route": ["PaymentCalculationAgent"],
        "capability_calls": ["payment.calculate"], "actual_answer": "旧答案",
        "expected_answer": "应核对地方政策", "correction_note": "地区政策不匹配",
        "added_to_eval": False, "fixed": False, "created_at": "2026-07-10T00:00:00+08:00",
    }]
