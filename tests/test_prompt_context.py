from pathlib import Path

from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext


def test_context_manager_never_trims_current_query():
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=1,
        user_query="上班路上发生交通事故，交警认定我不是主要责任，能不能认定工伤？",
    )
    manager = ContextManager(max_chars=30)

    sections, metadata = manager.build_sections(ctx)

    assert sections["current_query"] == ctx.request.user_query
    assert "current_query" not in metadata["trimmed_sections"]


def test_prompt_manager_loads_metadata_and_renders_sections():
    manager = PromptManager(Path("ananhu_agent/prompts/templates"))
    rendered = manager.render(
        prompt_id="domain_consultation.work_injury_recognition",
        sections={"current_query": "上班路上交通事故算工伤吗？"},
    )

    assert rendered.metadata["agent"] == "DomainConsultationAgent"
    assert "[Output Schema]" in rendered.text
    assert "上班路上交通事故算工伤吗？" in rendered.text
