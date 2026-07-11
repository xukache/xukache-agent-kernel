from __future__ import annotations

from ananhu_agent.schemas import AgentContext, AgentMessage, CapabilityCall


class PolicyRAGAgent:
    """政策检索 Agent。

    只生成 knowledge.search 能力意图，确保政策检索仍通过 CapabilityGateway 的权限和 trace 治理。
    """

    name = "PolicyRAGAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="检索政策依据。",
            capability_calls=[
                CapabilityCall(
                    call_id=f"{ctx.request.request_id}:knowledge-search",
                    capability_name="knowledge.search",
                    called_by=self.name,
                    input={
                        "query": ctx.request.user_query,
                        "trusted_jurisdiction": {
                            "province": ctx.request.province,
                            "city": ctx.request.city,
                        },
                        "top_k": 3,
                    },
                )
            ],
        )
