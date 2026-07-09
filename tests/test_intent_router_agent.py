from pathlib import Path

from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.models.fake_model import FakeModelClient
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext


def test_intent_router_extracts_payment_intent_and_slots_through_prompt_context():
    agent = IntentRouterAgent(
        FakeModelClient(),
        ContextManager(),
        PromptManager(Path("ananhu_agent/prompts/templates")),
    )
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
    )

    message = agent.run(ctx)

    assert message.data["intent"] == "payment_calculation"
    assert message.data["slots"]["province"] == "四川省"
    assert message.data["slots"]["disability_grade"] == "十级"
    assert message.data["slots"]["monthly_wage"] == 6000
    assert message.data["prompt_ref"] == "intent_router.v1"
