from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agno_adapters.agent_adapter import AgentRuntimeAdapter
from ananhu_agent.agno_adapters.tool_adapter import ToolRuntimeAdapter
from ananhu_agent.schemas import AgentContext


def test_agent_runtime_adapter_preserves_agent_message_contract():
    adapter = AgentRuntimeAdapter(DomainConsultationAgent())
    ctx = AgentContext.new_for_query("sess_1", 1, "劳动能力鉴定需要准备哪些材料？")

    message = adapter.run(ctx)

    assert message.agent_name == "DomainConsultationAgent"
    assert message.status == "success"


def test_tool_runtime_adapter_preserves_tool_handler_contract():
    adapter = ToolRuntimeAdapter(lambda payload: {"echo": payload["query"]})

    output = adapter.run({"query": "工伤认定"})

    assert output == {"echo": "工伤认定"}
