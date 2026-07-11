from pathlib import Path

from ananhu_agent.capabilities.contracts import CapabilityResult
from ananhu_agent.ports.knowledge_gateway import KnowledgeQuery, KnowledgeSearchResult
from ananhu_agent.schemas import AgentMessage


def test_agent_message_exposes_capability_calls_only():
    message = AgentMessage(agent_name="x", status="success", content="x")

    assert message.capability_calls == []
    assert not hasattr(message, "tool_" + "calls")


def test_capability_result_has_no_legacy_tool_projection():
    assert "tool_call_" + "result" not in CapabilityResult.model_fields


def test_knowledge_port_has_no_legacy_payload_projection():
    assert not hasattr(KnowledgeQuery, "from_" + "payload")
    assert not hasattr(KnowledgeSearchResult, "to_" + "tool_payload")


def test_legacy_protocol_symbols_are_absent_from_product_code():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path("ananhu_agent/schemas.py"),
            Path("ananhu_agent/capabilities/contracts.py"),
            Path("ananhu_agent/ports/knowledge_gateway.py"),
        )
    )

    for symbol in (
        "PolicyRAG" + "Tool",
        "search_" + "policy",
        "ToolCall" + "Request",
        "ToolCall" + "Result",
    ):
        assert symbol not in source
