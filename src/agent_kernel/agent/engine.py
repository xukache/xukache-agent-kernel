"""Agent 的最小异步执行循环。

当前 C3 只执行一次 Model.generate。多轮上限、Tool、Memory 和 Runtime 生命周期
由后续任务负责，本模块不提前拥有这些边界。
"""

from __future__ import annotations

import asyncio

from agent_kernel.contracts import ErrorInfo, ErrorSource
from agent_kernel.model import ModelError, ModelErrorCode, Usage

from .definition import AgentDefinition
from .errors import AgentErrorCode
from .request_builder import build_model_request
from .schemas import AgentInput, AgentResult, AgentStatus, AgentStopReason


async def run_agent(
    definition: AgentDefinition,
    agent_input: AgentInput,
) -> AgentResult:
    """执行一次 Agent -> Model -> Result 的最小链路。"""

    request = build_model_request(definition, agent_input)

    try:
        response = await definition.model.generate(request)
    except ModelError as exc:
        is_cancelled = exc.code is ModelErrorCode.CANCELLED
        return AgentResult(
            status=(
                AgentStatus.CANCELLED
                if is_cancelled
                else AgentStatus.FAILED
            ),
            usage=Usage(),
            stop_reason=(
                AgentStopReason.CANCELLED
                if is_cancelled
                else AgentStopReason.ERROR
            ),
            error=ErrorInfo(
                code=exc.code.value,
                message=str(exc),
                source=ErrorSource.MODEL,
                retryable=exc.retryable,
                details=exc.details,
            ),
        )
    except asyncio.CancelledError:
        return _cancelled_result()
    except Exception:
        return AgentResult(
            status=AgentStatus.FAILED,
            usage=Usage(),
            stop_reason=AgentStopReason.ERROR,
            error=ErrorInfo(
                code=AgentErrorCode.INTERNAL.value,
                message="Agent execution failed",
                source=ErrorSource.AGENT,
                retryable=False,
            ),
        )

    output = (
        response.structured_output
        if response.structured_output is not None
        else response.text
    )
    if output is None and response.tool_calls:
        return AgentResult(
            status=AgentStatus.FAILED,
            tool_calls=response.tool_calls,
            usage=response.usage,
            model_id=response.model_id,
            stop_reason=AgentStopReason.ERROR,
            error=ErrorInfo(
                code=AgentErrorCode.INTERNAL.value,
                message="Tool calls are not supported by the C3 Agent loop",
                source=ErrorSource.AGENT,
                retryable=False,
            ),
        )

    return AgentResult(
        status=AgentStatus.SUCCEEDED,
        output=output,
        tool_calls=response.tool_calls,
        usage=response.usage,
        model_id=response.model_id,
        stop_reason=AgentStopReason.COMPLETED,
    )


def _cancelled_result() -> AgentResult:
    """将 Python 任务取消转换为 Agent 的公开取消结果。"""

    return AgentResult(
        status=AgentStatus.CANCELLED,
        usage=Usage(),
        stop_reason=AgentStopReason.CANCELLED,
        error=ErrorInfo(
            code=AgentErrorCode.CANCELLED.value,
            message="Agent execution cancelled",
            source=ErrorSource.AGENT,
            retryable=False,
        ),
    )
