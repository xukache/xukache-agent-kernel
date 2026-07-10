from __future__ import annotations

from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ModelErrorCode(str, Enum):
    """模型失败的项目级分类，不向上游泄漏 provider 异常类型。"""

    CONFIGURATION = "configuration_error"
    AUTHENTICATION = "authentication_error"
    RATE_LIMIT = "rate_limit_error"
    TIMEOUT = "timeout_error"
    PROVIDER = "provider_error"
    RESPONSE_FORMAT = "response_format_error"
    OUTPUT_SCHEMA = "output_schema_error"


class ModelRequest(BaseModel):
    """一次结构化模型调用的框架中立输入。"""

    schema_version: str = "model-request.v1"
    run_id: str
    request_id: str
    session_id: str
    node_id: str
    logical_call_id: str
    attempt: int = Field(default=1, ge=1)
    profile: str
    prompt_ref: str
    prompt: str
    output_schema: dict[str, Any] = Field(default_factory=dict)
    temperature: float | None = None


class ModelUsage(BaseModel):
    """由项目维护的模型用量口径。"""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float | None = None
    currency: str | None = None
    usage_source: str
    reported: bool = False


class ModelResult(BaseModel):
    """结构化模型结果及可审计的 provider 元数据。"""

    schema_version: str = "model-result.v1"
    output: dict[str, Any]
    provider: str
    model: str
    profile: str
    finish_reason: str | None = None
    provider_request_id: str | None = None
    usage: ModelUsage
    latency_ms: int = 0
    attempt: int = 1
    reasoning_content: str | None = Field(default=None, exclude=True, repr=False)


class ModelGatewayError(Exception):
    """可安全写入 trace 的归一化模型异常。"""

    def __init__(
        self,
        code: ModelErrorCode,
        message: str,
        *,
        provider: str,
        retryable: bool,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code


class ModelGateway(Protocol):
    """供应用阶段调用的 async 模型端口。"""

    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        """生成并校验结构化输出。"""

        ...
