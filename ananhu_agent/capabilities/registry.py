from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


CapabilityHandler = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]
CapabilityOutputValidator = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class CapabilityDefinition:
    """一个显式注册能力的治理和执行定义。"""

    name: str
    description: str
    risk_level: str
    timeout_ms: int
    allowed_callers: tuple[str, ...]
    required_input_keys: tuple[str, ...]
    output_required_keys: tuple[str, ...]
    handler: CapabilityHandler
    output_validator: CapabilityOutputValidator | None = None


class CapabilityRegistry:
    """能力白名单；未知能力不能通过运行时动态发现。"""

    def __init__(self) -> None:
        self._definitions: dict[str, CapabilityDefinition] = {}

    def register(self, definition: CapabilityDefinition) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"duplicate capability: {definition.name}")
        self._definitions[definition.name] = definition

    def get(self, name: str) -> CapabilityDefinition | None:
        return self._definitions.get(name)

    def names(self) -> tuple[str, ...]:
        """返回稳定排序后的显式能力名，供组合根和验收检查使用。"""
        return tuple(sorted(self._definitions))
