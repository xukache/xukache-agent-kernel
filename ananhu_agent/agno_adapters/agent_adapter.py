from __future__ import annotations

from typing import Protocol

from ananhu_agent.schemas import AgentContext, AgentMessage


class AgentRuntime(Protocol):
    """MVP 无状态 Agent 的最小运行协议。"""

    name: str

    def run(self, ctx: AgentContext) -> AgentMessage:
        """根据只读上下文返回结构化 AgentMessage。"""


class AgentRuntimeAdapter:
    """Agno Agent 接入前的轻量运行时适配器。

    当前 MVP 不绑定真实 Agno runtime；该适配器把现有无状态 Agent 暴露成稳定的
    `run(ctx)` 边界，后续接 Agno Team / Workflow 时仍保持 AgentMessage 协议。
    """

    def __init__(self, agent: AgentRuntime) -> None:
        self.agent = agent
        self.name = agent.name

    def run(self, ctx: AgentContext) -> AgentMessage:
        """转发到被包装 Agent，不写状态、不调用工具。"""

        return self.agent.run(ctx)
