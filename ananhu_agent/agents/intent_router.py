from __future__ import annotations

from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.models.fake_model import FakeModelClient
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
        model_client: FakeModelClient,
        context_manager: ContextManager,
        prompt_manager: PromptManager,
    ) -> None:
        self.model_client = model_client
        self.context_manager = context_manager
        self.prompt_manager = prompt_manager

    def run(self, ctx: AgentContext) -> AgentMessage:
        sections, context_metadata = self.context_manager.build_sections(ctx)
        rendered = self.prompt_manager.render("intent_router.v1", sections)
        result = self.model_client.classify_and_extract(rendered.text)
        result["prompt_ref"] = rendered.metadata["id"]
        result["prompt_metadata"] = rendered.metadata
        result["context_metadata"] = context_metadata

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
