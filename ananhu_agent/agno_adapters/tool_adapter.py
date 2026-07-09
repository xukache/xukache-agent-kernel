from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ToolRuntimeAdapter:
    """Agno Tool 接入前的轻量工具适配器。

    适配器只包装纯 handler；权限、schema、超时、trace 仍由 ToolExecutor 统一处理。
    """

    def __init__(self, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self.handler = handler

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """按现有 Tool handler 契约返回结构化 dict。"""

        return self.handler(payload)
