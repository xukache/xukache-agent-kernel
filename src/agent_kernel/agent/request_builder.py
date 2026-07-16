"""Agent 到 Model 的基础请求组装。

本模块只负责确定性数据转换，不调用 Model，也不拥有 Tool、Memory 或 Runtime
上下文的装配职责。
"""

from agent_kernel.model import ModelRequest

from .definition import AgentDefinition
from .schemas import AgentInput


def build_model_request(
    definition: AgentDefinition,
    agent_input: AgentInput,
) -> ModelRequest:
    """将 C1 的 Definition / Input 转换为一次 Provider Neutral 请求。"""

    return ModelRequest(
        instructions=definition.instructions,
        input=agent_input.input,
        output_schema=agent_input.output_schema,
    )
