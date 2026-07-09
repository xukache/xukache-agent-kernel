from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator


def test_orchestrator_answers_payment_question_with_trace(tmp_path):
    orchestrator = create_default_orchestrator(tmp_path)

    ctx = orchestrator.ask(
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
    )

    assert ctx.final_answer is not None
    assert "一次性伤残补助金" in ctx.final_answer
    assert "42000" in ctx.final_answer
    assert "以经办机构和正式材料为准" in ctx.final_answer
    events = orchestrator.trace_recorder.read_all()
    event_types = [event["event_type"] for event in events]
    assert event_types[0] == "request_received"
    assert "intent_recognized" in event_types
    assert "intent_revised" in event_types
    assert "slots_merged" in event_types
    assert "prompt_built" in event_types
    assert "model_called" in event_types
    assert "tool_finished" in event_types
    assert "answer_validated" in event_types
    assert "safety_checked" in event_types
    assert "response_ready" in event_types
    assert orchestrator.task_state_store.read_all()[0]["current_phase"] == "response_ready"
    assert orchestrator.report_store.read_all()[0]["final_intent"] == "payment_calculation"
