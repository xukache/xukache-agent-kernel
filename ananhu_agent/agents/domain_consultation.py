from __future__ import annotations

from ananhu_agent.schemas import AgentContext, AgentMessage


class DomainConsultationAgent:
    """政策咨询 Agent。

    MVP 阶段只声明需要政策依据，由编排器串行安排 PolicyRAGAgent 检索；
    该 Agent 不直接调用底层工具。
    """

    name = "DomainConsultationAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="需要检索政策依据后回答。",
            data={"needs_policy_evidence": True},
            capability_calls=[],
        )
