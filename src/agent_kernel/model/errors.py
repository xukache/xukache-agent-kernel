"""Model Core 的 Provider Neutral 运行时错误。"""

from __future__ import annotations

from enum import Enum

from agent_kernel.contracts import JsonObject, KernelError


class ModelErrorCode(str, Enum):
    """Model 调用可以被上层治理的稳定错误类别。"""

    PROVIDER = "model.provider"
    TIMEOUT = "model.timeout"
    RATE_LIMIT = "model.rate_limit"
    FORMAT = "model.format"
    CANCELLED = "model.cancelled"


class ModelError(KernelError):
    """Model Adapter 边界向上层传播的错误。

    具体 Provider Exception 必须在 Adapter 内部转换成该错误，不能把 SDK
    类型泄漏到 Agent、Runtime 或公共证据。
    """

    def __init__(
        self,
        code: ModelErrorCode,
        message: str,
        *,
        retryable: bool = False,
        details: JsonObject | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.details = details or {}
