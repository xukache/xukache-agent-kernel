from __future__ import annotations

from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.ports.model_gateway import ModelGateway, ModelRequest
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext, AgentMessage


class IntentRouterAgent:
    """意图识别 Agent。

    Agent 保持无状态：只读取 AgentContext，通过 PromptManager / ContextManager 构造模型输入，
    并把结构化识别结果交回编排器。
    """

    name = "IntentRouterAgent"

    def __init__(
        self,
        model_gateway: ModelGateway,
        context_manager: ContextManager,
        prompt_manager: PromptManager,
    ) -> None:
        self.model_gateway = model_gateway
        self.context_manager = context_manager
        self.prompt_manager = prompt_manager

    async def run(
        self,
        ctx: AgentContext,
        *,
        run_id: str | None = None,
        node_id: str = "understand",
        logical_call_id: str | None = None,
    ) -> AgentMessage:
        sections, context_metadata = self.context_manager.build_sections(ctx)
        rendered = self.prompt_manager.render("intent_router.v1", sections)
        model_result = await self.model_gateway.generate_structured(ModelRequest(
            run_id=run_id or ctx.request.request_id,
            request_id=ctx.request.request_id,
            node_id=node_id,
            logical_call_id=logical_call_id or f"{ctx.request.request_id}:{node_id}:model",
            profile=rendered.metadata["model_profile"],
            prompt_ref=rendered.metadata["id"],
            prompt=rendered.text,
            output_schema={
                "type": "object",
                "required": [
                    "intent", "confidence", "slots", "missing_slots", "is_composite",
                ],
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [
                            "work_injury_recognition", "labor_capacity",
                            "insurance_participation", "payment_calculation", "other",
                        ],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "slots": {
                        "type": "object",
                        "properties": {
                            "province": {
                                "type": "string",
                                "description": "省级行政区全称，例如四川省。",
                            },
                            "city": {"type": "string"},
                            "disability_grade": {"type": "string"},
                            "monthly_wage": {"type": "number"},
                            "incident_date": {"type": "string"},
                            "insured": {"type": "boolean"},
                            "employer_status": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                    "missing_slots": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "只列出当前意图继续处理所必需且用户尚未提供的字段；"
                            "不要列出可选字段。待遇测算已有 province、"
                            "disability_grade、monthly_wage 时返回空数组。"
                        ),
                    },
                    "is_composite": {"type": "boolean"},
                },
            },
        ))
        result = dict(model_result.output)
        result["prompt_ref"] = rendered.metadata["id"]
        result["prompt_metadata"] = rendered.metadata
        result["context_metadata"] = context_metadata
        result["model_result"] = model_result.model_dump(exclude={"output"})

        return AgentMessage(
            agent_name=self.name,
            status="success",
            content=f"识别为 {result['intent']}",
            data=result,
            tool_calls=[],
            missing_slots=result["missing_slots"],
            citations=[],
            warnings=[],
        )
