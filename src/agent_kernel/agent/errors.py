"""Agent 边界拥有的稳定错误码。"""

from enum import Enum


class AgentErrorCode(str, Enum):
    """C1 已确认的 Agent 错误类别。"""

    LIMIT = "agent.limit"
    CANCELLED = "agent.cancelled"
    INTERNAL = "agent.internal"
