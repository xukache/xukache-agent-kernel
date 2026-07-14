"""Model Core 的可替换行为契约。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .schemas import ModelRequest, ModelResponse, ModelStreamChunk


@runtime_checkable
class Model(Protocol):
    """Provider Neutral 的异步模型能力。

    `generate` 返回一次完整响应；`stream` 返回有序增量。协议不关心
    Provider 客户端、凭证、HTTP 细节或具体取消实现。
    """

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """生成一次完整的 ModelResponse。"""
        ...

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        """返回一次只能消费一次的异步增量流。"""
        ...
