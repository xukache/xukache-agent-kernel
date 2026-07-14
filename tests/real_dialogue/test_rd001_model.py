"""RD-001：真实 Provider 下的结构化 Model 验收。"""

from __future__ import annotations

import os
import time

import pytest

from adapters.model import VolcengineArkConfig, VolcengineArkModel
from agent_kernel.model import FinishReason, ModelError, ModelErrorCode, ModelRequest
from agent_kernel.model import ModelResponse
from tests.support.real_dialogue_evidence import (
    EvidenceRecorder,
    EvidenceStatus,
    FailureDetails,
    create_evidence_context,
    evidence_root,
)

RD001_INPUT = "请计算 18 + 24，并按指定 JSON Schema 返回 result 整数。"
RD001_SCHEMA = {
    "type": "object",
    "properties": {"result": {"type": "integer"}},
    "required": ["result"],
    "additionalProperties": False,
}


def test_rd001_real_model_returns_structured_result() -> None:
    """真实 Smoke 开启时访问 Provider，否则只记录 NOT RUN。"""
    context = create_evidence_context("RD-001")
    recorder = EvidenceRecorder(evidence_root())
    smoke_enabled = os.getenv("ANANHU_REAL_MODEL_SMOKE") == "1"
    expected = {
        "structured_output.result": 42,
        "finish_reason": FinishReason.STOP.value,
    }

    if not smoke_enabled:
        recorder.write(
            context=context,
            model_id="not-run",
            provider="volcengine",
            raw_dialogue_input=RD001_INPUT,
            expected_structured_assertions=expected,
            actual_output_summary={},
            events=[],
            usage={},
            latency=0.0,
            error_type=None,
            retry_count=0,
            status=EvidenceStatus.NOT_RUN,
        )
        return

    started_at = time.perf_counter()
    try:
        config = VolcengineArkConfig.from_environment()
        model = VolcengineArkModel(config)
        response = _run_generation(
            model,
            ModelRequest(
                input=RD001_INPUT,
                output_schema=RD001_SCHEMA,
            ),
        )
    except (ImportError, OSError, ValueError, ModelError) as exc:
        latency = time.perf_counter() - started_at
        status = (
            EvidenceStatus.BLOCKED
            if not isinstance(exc, ModelError)
            or exc.code
            in {
                ModelErrorCode.PROVIDER,
                ModelErrorCode.TIMEOUT,
                ModelErrorCode.RATE_LIMIT,
            }
            else EvidenceStatus.FAIL
        )
        recorder.write(
            context=context,
            model_id="unknown",
            provider="volcengine",
            raw_dialogue_input=RD001_INPUT,
            expected_structured_assertions=expected,
            actual_output_summary={},
            events=[],
            usage={},
            latency=latency,
            error_type=type(exc).__name__,
            retry_count=0,
            status=status,
            failure=FailureDetails(
                expected="真实 Provider 返回结构化 result == 42",
                actual=str(exc),
                failure_stage="model.generate",
                reproducible_command=(
                    "set -a; source .env; set +a; "
                    "ANANHU_REAL_MODEL_SMOKE=1 uv run pytest -q "
                    "tests/real_dialogue/test_rd001_model.py"
                ),
            ),
        )
        if status is EvidenceStatus.FAIL:
            raise
        return

    latency = time.perf_counter() - started_at
    actual = {
        "structured_output": response.structured_output or {},
        "finish_reason": response.finish_reason.value,
        "model_id": response.model_id,
    }
    usage = response.usage.model_dump(mode="json")
    passed = (
        response.structured_output is not None
        and response.structured_output.get("result") == 42
        and response.finish_reason is FinishReason.STOP
    )
    recorder.write(
        context=context,
        model_id=response.model_id,
        provider="volcengine",
        raw_dialogue_input=RD001_INPUT,
        expected_structured_assertions=expected,
        actual_output_summary=actual,
        events=[],
        usage=usage,
        latency=latency,
        error_type=None if passed else "assertion",
        retry_count=0,
        status=EvidenceStatus.PASS if passed else EvidenceStatus.FAIL,
        failure=(
            None
            if passed
            else FailureDetails(
                expected="structured_output.result == 42 and finish_reason == stop",
                actual=actual,
                failure_stage="rd001.assertion",
                reproducible_command=(
                    "set -a; source .env; set +a; "
                    "ANANHU_REAL_MODEL_SMOKE=1 uv run pytest -q "
                    "tests/real_dialogue/test_rd001_model.py"
                ),
            )
        ),
    )
    assert passed, actual


def _run_generation(
    model: VolcengineArkModel,
    request: ModelRequest,
) -> ModelResponse:
    import asyncio

    return asyncio.run(model.generate(request))
