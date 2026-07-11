from __future__ import annotations

from ananhu_agent.schemas import AgentContext, AgentMessage, CapabilityCall


class PaymentCalculationAgent:
    """待遇测算 Agent。

    Agent 只根据已识别槽位发出测算能力意图，实际执行由 CapabilityGateway 统一完成。
    """

    name = "PaymentCalculationAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        slots = ctx.intent_result.slots if ctx.intent_result else {}
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="需要测算待遇并补充政策依据。",
            capability_calls=[
                CapabilityCall(
                    call_id=f"{ctx.request.request_id}:payment-calculation",
                    capability_name="payment.calculate",
                    called_by=self.name,
                    input={
                        "province": slots.get("province"),
                        "disability_grade": slots.get("disability_grade"),
                        "monthly_wage": slots.get("monthly_wage"),
                    },
                ),
            ],
        )
