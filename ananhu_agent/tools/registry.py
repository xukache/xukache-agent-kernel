from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """工具注册元数据。

    Agent 只能依赖这里声明的调用边界，不能直接持有或调用底层 handler。
    """

    name: str
    description: str
    risk_level: str
    timeout_ms: int
    allowed_callers: list[str]
    required_input_keys: list[str]
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """MVP 工具注册表，作为 ToolExecutor 的唯一工具发现入口。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)
