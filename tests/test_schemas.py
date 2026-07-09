from ananhu_agent.schemas import (
    AgentContext,
    AgentMessage,
    RequestContext,
    RunReport,
    TaskState,
    ToolCallResult,
    TraceEvent,
)


def test_agent_context_contains_required_runtime_sections():
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤大概能赔多少钱？",
        province="四川省",
        city="成都市",
    )

    assert ctx.request.user_query == "四川十级工伤大概能赔多少钱？"
    assert ctx.intent_result is None
    assert ctx.tool_results == []
    assert ctx.agent_outputs == []
    assert ctx.final_answer is None


def test_agent_message_is_structured():
    message = AgentMessage(
        agent_name="IntentRouterAgent",
        status="success",
        content="识别为待遇测算",
        data={"intent": "payment_calculation"},
        tool_calls=[],
        missing_slots=[],
        citations=[],
        warnings=[],
    )

    assert message.agent_name == "IntentRouterAgent"
    assert message.data["intent"] == "payment_calculation"


def test_tool_call_result_and_trace_event_are_serializable():
    request = RequestContext.new(
        session_id="sess_1",
        turn_id=1,
        user_query="劳动能力鉴定要什么材料？",
    )
    result = ToolCallResult(
        tool_call_id="tool_001",
        tool_name="PolicyRAGTool",
        called_by="PolicyRAGAgent",
        tool_status="success",
        tool_error_code=None,
        latency_ms=12,
        input={"query": request.user_query},
        output={"documents": []},
        fallback_used=False,
    )
    event = TraceEvent.new(
        request_id=request.request_id,
        session_id=request.session_id,
        event_type="tool_finished",
        phase="tool",
        payload=result.model_dump(),
        latency_ms=12,
    )

    assert event.payload["tool_name"] == "PolicyRAGTool"
    assert event.created_at.endswith("+08:00")


def test_task_state_and_run_report_capture_runtime_evidence():
    state = TaskState(
        id="state_1",
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤大概能赔多少钱？",
        status="completed",
        current_phase="response_ready",
        raw_intent="payment_calculation",
        revised_intent="payment_calculation",
        active_slots={"province": "四川省"},
        missing_slots=[],
        route_agents=["PaymentCalculationAgent", "PolicyRAGAgent"],
        prompt_refs=["intent_router.v1"],
        tool_steps=["PaymentCalculationTool", "PolicyRAGTool"],
        model_attempts=1,
        fallback_used=False,
        error_message=None,
    )
    report = RunReport(
        id="report_1",
        session_id="sess_1",
        final_status="success",
        final_intent="payment_calculation",
        route_agents=["PaymentCalculationAgent", "PolicyRAGAgent"],
        tool_count=2,
        model_attempts=1,
        prompt_refs=["intent_router.v1"],
        prompt_metadata={"intent_router.v1": {"version": "v1"}},
        output_schema_valid_rate=1.0,
        token_usage={},
        latency_ms=10,
        fallback_used=False,
        safety_result={"passed": True},
        badcase_candidate=False,
    )

    assert state.current_phase == "response_ready"
    assert report.tool_count == 2
