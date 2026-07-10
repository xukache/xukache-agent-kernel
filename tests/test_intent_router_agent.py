import asyncio
from pathlib import Path

from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.infrastructure.models.fake import FakeModelGateway
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext


class CapturingFakeModelGateway(FakeModelGateway):
    request = None

    async def generate_structured(self, request):
        self.request = request
        return await super().generate_structured(request)


def test_intent_router_extracts_payment_intent_and_slots_through_prompt_context():
    agent = IntentRouterAgent(
        FakeModelGateway(),
        ContextManager(),
        PromptManager(Path("ananhu_agent/prompts/templates")),
    )
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
    )

    message = asyncio.run(agent.run(ctx))

    assert message.data["intent"] == "payment_calculation"
    assert message.data["slots"]["province"] == "四川省"
    assert message.data["slots"]["disability_grade"] == "十级"
    assert message.data["slots"]["monthly_wage"] == 6000
    assert message.data["prompt_ref"] == "intent_router.v1"
    assert message.data["model_result"]["provider"] == "fake"
    assert message.data["model_result"]["usage"]["usage_source"] == "fake"


def test_intent_router_schema_explains_canonical_slots_and_required_missing_fields():
    gateway = CapturingFakeModelGateway()
    agent = IntentRouterAgent(
        gateway,
        ContextManager(),
        PromptManager(Path("ananhu_agent/prompts/templates")),
    )
    ctx = AgentContext.new_for_query(
        session_id="sess_schema",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
    )

    asyncio.run(agent.run(ctx))

    assert gateway.request is not None
    properties = gateway.request.output_schema["properties"]
    assert "行政区全称" in properties["slots"]["properties"]["province"]["description"]
    assert "当前意图" in properties["missing_slots"]["description"]
