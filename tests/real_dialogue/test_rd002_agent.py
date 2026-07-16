"""RD-002：真实 Provider 下的 Agent 结构化任务验收。"""

from __future__ import annotations

import asyncio
import os
import time

from adapters.model import VolcengineArkConfig, VolcengineArkModel
from agent_kernel.agent import (
    AgentDefinition,
    AgentInput,
    AgentStatus,
    AgentStopReason,
    run_agent,
)
from agent_kernel.model import ModelError, ModelErrorCode
from tests.support.real_dialogue_evidence import (
    EvidenceRecorder,
    EvidenceStatus,
    FailureDetails,
    create_evidence_context,
    evidence_root,
)

RD002_INPUT = "请完成任务：计算 9 + 6，并返回结构化结果。"
RD002_SCHEMA = {
    "type": "object",
    "properties": {"result": {"type": "integer"}},
    "required": ["result"],
    "additionalProperties": False,
}
RD002_INSTRUCTIONS = (
    "You are a calculator. Return only JSON matching the requested schema. "
    "Do not add extra fields."
)


def test_rd002_real_agent_returns_structured_result() -> None:
    """真实 Smoke 开启时运行 Agent，否则只记录 NOT RUN。"""
    context = create_evidence_context("RD-002")
    recorder = EvidenceRecorder(evidence_root())
    smoke_enabled = os.getenv("ANANHU_REAL_MODEL_SMOKE") == "1"
    expected = {
        "agent_result.status": AgentStatus.SUCCEEDED.value,
        "agent_result.output.result": 15,
        "agent_result.stop_reason": AgentStopReason.COMPLETED.value,
        "model_request.input": RD002_INPUT,
    }

    if not smoke_enabled:
        recorder.write(
            context=context,
            model_id="not-run",
            provider="volcengine",
            raw_dialogue_input=RD002_INPUT,
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
    request_summary = {
        "instructions": RD002_INSTRUCTIONS,
        "input": RD002_INPUT,
        "output_schema": RD002_SCHEMA,
    }

    try:
        config = VolcengineArkConfig.from_environment()
        model = VolcengineArkModel(config)
        definition = AgentDefinition(
            definition_id="rd002-calculator",
            revision="1",
            instructions=RD002_INSTRUCTIONS,
            model=model,
            max_model_rounds=1,
        )
        result = asyncio.run(
            run_agent(
                definition,
                AgentInput(
                    input=RD002_INPUT,
                    output_schema=RD002_SCHEMA,
                ),
            )
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
            raw_dialogue_input=RD002_INPUT,
            expected_structured_assertions=expected,
            actual_output_summary={"model_request": request_summary},
            events=[],
            usage={},
            latency=latency,
            error_type=type(exc).__name__,
            retry_count=0,
            status=status,
            failure=FailureDetails(
                expected="AgentResult.output.result == 15 and stop_reason == completed",
                actual=str(exc),
                failure_stage="agent.run",
                reproducible_command=_reproducible_command(),
            ),
        )
        if status is EvidenceStatus.FAIL:
            raise
        return

    latency = time.perf_counter() - started_at
    actual = {
        "model_request": request_summary,
        "agent_result": result.model_dump(mode="json"),
    }
    passed = (
        result.status is AgentStatus.SUCCEEDED
        and isinstance(result.output, dict)
        and result.output.get("result") == 15
        and result.stop_reason is AgentStopReason.COMPLETED
        and result.model_id is not None
        and result.usage.model_dump(mode="json") is not None
    )
    result_model_id = result.model_id or "unknown"
    recorder.write(
        context=context,
        model_id=result_model_id,
        provider="volcengine",
        raw_dialogue_input=RD002_INPUT,
        expected_structured_assertions=expected,
        actual_output_summary=actual,
        events=[],
        usage=result.usage.model_dump(mode="json"),
        latency=latency,
        error_type=None if passed else "assertion",
        retry_count=0,
        status=EvidenceStatus.PASS if passed else EvidenceStatus.FAIL,
        failure=(
            None
            if passed
            else FailureDetails(
                expected="AgentResult.output.result == 15 and stop_reason == completed",
                actual=actual,
                failure_stage="rd002.assertion",
                reproducible_command=_reproducible_command(),
            )
        ),
    )
    assert passed, actual


def _reproducible_command() -> str:
    return (
        "set -a; source .env; set +a; "
        "export ANANHU_REAL_MODEL_SMOKE=1; "
        "unset ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy; "
        "uv run pytest -q tests/real_dialogue/test_rd001_model.py "
        "tests/real_dialogue/test_rd002_agent.py"
    )
