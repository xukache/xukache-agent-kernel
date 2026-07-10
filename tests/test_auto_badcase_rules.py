import asyncio

from ananhu_agent.orchestrator.badcase_rules import detect_badcase_issues
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.storage.runtime_stores import ReportStore
from ananhu_agent.workflow.contracts import RunRequest, WorkflowState


def test_detects_missing_citation_and_low_confidence():
    state = WorkflowState(
        run_id="run_1",
        request_id="req_1",
        session_id="sess_1",
        intent_result={"intent": "other", "confidence": 0.4, "missing_slots": ["province"]},
        verification_result={"passed": False, "issues": ["missing_citation"]},
        safety_result={"passed": True, "warnings": []},
    )

    issues = detect_badcase_issues(state)

    assert "low_intent_confidence" in issues
    assert "missing_citation" in issues


def test_native_runtime_records_automatic_badcase_candidates(tmp_path):
    runtime = create_default_runtime(tmp_path)

    asyncio.run(runtime.invoke(RunRequest(
        run_id="run_badcase",
        request_id="req_badcase",
        session_id="sess_1",
        turn_id=1,
        user_query="这个能不能算？",
        created_at="2026-07-10T00:00:00+08:00",
    )))

    badcases = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "low_intent_confidence" in badcases
    assert "empty_answer" in badcases
    report = ReportStore(tmp_path / "run_reports.jsonl").read_all()[0]
    assert report["badcase_candidate"] is True
