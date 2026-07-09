from ananhu_agent.orchestrator.badcase_rules import detect_badcase_issues
from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator
from ananhu_agent.schemas import AgentContext, IntentResult, SafetyResult, VerificationResult


def test_detects_missing_citation_and_low_confidence():
    ctx = AgentContext.new_for_query("sess_1", 1, "这个能不能算？")
    ctx.intent_result = IntentResult(intent="other", confidence=0.4, missing_slots=["province"])
    ctx.verification_result = VerificationResult(passed=False, issues=["missing_citation"])
    ctx.safety_result = SafetyResult(passed=True)

    issues = detect_badcase_issues(ctx)

    assert "low_intent_confidence" in issues
    assert "missing_citation" in issues


def test_orchestrator_records_automatic_badcase_candidates(tmp_path):
    orchestrator = create_default_orchestrator(tmp_path)

    orchestrator.ask("sess_1", 1, "这个能不能算？")

    badcases = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "rag_no_result" in badcases
    assert "missing_citation" in badcases
    report = orchestrator.report_store.read_all()[0]
    assert report["badcase_candidate"] is True
