"""共享 ErrorInfo 的确定性合同测试。"""

import json

import pytest
from pydantic import ValidationError

from agent_kernel.contracts import ErrorInfo, ErrorSource


def test_error_info_is_strict_immutable_and_json_serializable() -> None:
    source_details = {"provider": {"request_ids": ["request-1"]}}
    error = ErrorInfo(
        code="model.timeout",
        message="model request timed out",
        source=ErrorSource.MODEL,
        retryable=True,
        details=source_details,
    )

    source_details["provider"]["request_ids"].append("request-2")

    assert error.details == {"provider": {"request_ids": ["request-1"]}}
    assert json.loads(error.model_dump_json())["code"] == "model.timeout"

    with pytest.raises(TypeError, match="frozen JSON"):
        error.details["provider"]["request_ids"].append("mutated")  # type: ignore[index]

    with pytest.raises(ValidationError):
        ErrorInfo(
            code="model.timeout",
            message="timeout",
            source=ErrorSource.MODEL,
            retryable=1,
        )


@pytest.mark.parametrize("code", ["", "timeout", "Model.Timeout", "model timeout"])
def test_error_info_rejects_invalid_error_codes(code: str) -> None:
    with pytest.raises(ValidationError):
        ErrorInfo(
            code=code,
            message="invalid",
            source=ErrorSource.MODEL,
            retryable=False,
        )


def test_error_info_rejects_blank_message_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ErrorInfo(
            code="agent.internal",
            message="   ",
            source=ErrorSource.AGENT,
            retryable=False,
        )

    with pytest.raises(ValidationError):
        ErrorInfo(
            code="agent.internal",
            message="internal failure",
            source=ErrorSource.AGENT,
            retryable=False,
            traceback="secret",
        )
