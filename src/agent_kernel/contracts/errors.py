"""Kernel 运行时错误与公开失败证据。"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from .schemas import JsonObject, KernelSchema


class KernelError(Exception):
    """合法运行中的 Kernel 失败传播基类。

    各 Core 可以定义自己的稳定错误类型，但不能把 Provider SDK Exception
    直接暴露到 Kernel 公共调用边界。
    """


class ErrorSource(str, Enum):
    """当前已确认的错误所有者。"""

    AGENT = "agent"
    MODEL = "model"


class ErrorInfo(KernelSchema):
    """Result 和 Event 使用的脱敏、可序列化失败证据。"""

    code: str = Field(
        min_length=3,
        pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$",
    )
    message: str = Field(min_length=1)
    source: ErrorSource
    retryable: bool
    details: JsonObject = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("error message must not be blank")
        return value
