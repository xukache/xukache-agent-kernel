from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.schemas import AgentContext, IntentResult


def test_domain_agent_returns_structured_need_for_policy_evidence():
    ctx = AgentContext.new_for_query("sess_1", 1, "上班路上交通事故算工伤吗？")
    ctx.intent_result = IntentResult(intent="work_injury_recognition", confidence=0.9)

    message = DomainConsultationAgent().run(ctx)

    assert message.agent_name == "DomainConsultationAgent"
    assert message.data["needs_policy_evidence"] is True
    assert message.capability_calls == []


def test_payment_agent_requests_payment_capability():
    ctx = AgentContext.new_for_query("sess_1", 1, "四川十级工伤月工资6000赔多少钱？")
    ctx.intent_result = IntentResult(
        intent="payment_calculation",
        confidence=0.9,
        slots={"province": "四川省", "disability_grade": "十级", "monthly_wage": 6000},
    )

    message = PaymentCalculationAgent().run(ctx)

    assert [call.capability_name for call in message.capability_calls] == ["payment.calculate"]


def test_policy_rag_agent_requests_knowledge_capability():
    from ananhu_agent.agents.policy_rag import PolicyRAGAgent

    ctx = AgentContext.new_for_query("sess_1", 1, "劳动能力鉴定需要准备哪些材料？")
    message = PolicyRAGAgent().run(ctx)

    assert message.capability_calls[0].capability_name == "knowledge.search"
    assert message.capability_calls[0].called_by == "PolicyRAGAgent"
