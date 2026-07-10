from __future__ import annotations

from ananhu_agent.schemas import AgentContext, AgentMessage, ToolCallRequest


class PolicyRAGAgent:
    """政策检索 Agent。

    只生成 PolicyRAGTool 调用请求，确保政策检索仍通过 ToolExecutor 的权限和 trace 治理。
    """

    name = "PolicyRAGAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="检索政策依据。",
            tool_calls=[
                ToolCallRequest(
                    tool_call_id=f"{ctx.request.request_id}:policy-rag",
                    tool_name="PolicyRAGTool",
                    called_by=self.name,
                    input={
                        "query": ctx.request.user_query,
                        "province": ctx.request.province,
                        "city": ctx.request.city,
                        "top_k": 3,
                    },
                )
            ],
        )
