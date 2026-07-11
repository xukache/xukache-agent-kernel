from ananhu_agent.capabilities.contracts import (
    CapabilityIdempotency,
    CapabilityPolicy,
    CapabilityResult,
    CapabilityStatus,
)
from ananhu_agent.schemas import (
    AgentContext,
    AgentMessage,
    CapabilityCall,
    RequestContext,
    RunReport,
    TaskState,
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
    assert ctx.capability_results == []
    assert ctx.agent_outputs == []
    assert ctx.final_answer is None


def test_agent_message_is_structured():
    message = AgentMessage(
        agent_name="IntentRouterAgent",
        status="success",
        content="识别为待遇测算",
        data={"intent": "payment_calculation"},
        capability_calls=[],
        missing_slots=[],
        citations=[],
        warnings=[],
    )

    assert message.agent_name == "IntentRouterAgent"
    assert message.data["intent"] == "payment_calculation"


def test_capability_result_and_trace_event_are_serializable():
    request = RequestContext.new(
        session_id="sess_1",
        turn_id=1,
        user_query="劳动能力鉴定要什么材料？",
    )
    result = CapabilityResult(
        request_id=request.request_id,
        session_id=request.session_id,
        capability_name="knowledge.search",
        caller="PolicyRAGAgent",
        node_id="execute",
        logical_call_id="call_001",
        attempt=1,
        status=CapabilityStatus.SUCCESS,
        policy=CapabilityPolicy(
            risk_level="read_only",
            timeout_ms=3000,
            idempotency=CapabilityIdempotency.READ_ONLY_REPEATABLE,
        ),
        output={"evidences": []},
    )
    event = TraceEvent.new(
        request_id=request.request_id,
        session_id=request.session_id,
        event_type="capability_finished",
        phase="capability",
        payload=result.model_dump(),
        latency_ms=12,
    )

    assert event.payload["capability_name"] == "knowledge.search"
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
        capability_steps=["payment.calculate", "knowledge.search"],
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
        capability_count=2,
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
    assert report.capability_count == 2
