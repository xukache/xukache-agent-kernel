from __future__ import annotations

from uuid import uuid4

from ananhu_agent.schemas import AgentContext, AgentMessage, ToolCallRequest


class PaymentCalculationAgent:
    """待遇测算 Agent。

    Agent 只根据已识别槽位发出测算工具请求，实际执行由 ToolExecutor 统一完成。
    """

    name = "PaymentCalculationAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        slots = ctx.intent_result.slots if ctx.intent_result else {}
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="需要测算待遇并补充政策依据。",
            tool_calls=[
                ToolCallRequest(
                    tool_call_id=f"tool_{uuid4().hex[:8]}",
                    tool_name="PaymentCalculationTool",
                    called_by=self.name,
                    input={
                        "province": slots.get("province"),
                        "disability_grade": slots.get("disability_grade"),
                        "monthly_wage": slots.get("monthly_wage"),
                    },
                ),
            ],
        )
