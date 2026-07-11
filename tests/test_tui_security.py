from __future__ import annotations

import asyncio
import json
import secrets
import subprocess
from pathlib import Path

import pytest
from pydantic import SecretStr

from ananhu_agent.cli.tui.presentation import sanitize
from ananhu_agent.models.observable_gateway import ObservableModelGateway, TransientSanitizer
from ananhu_agent.ports.model_gateway import ModelRequest, ModelResult, ModelUsage
from ananhu_agent.ports.run_event_sink import (
    ModelFinishedEvent,
    ModelFinishedPayload,
    NodeStartedEvent,
    NoOpRunEventSink,
    RunFinishedEvent,
    RunTransientPayload,
)
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.storage.runtime_stores import (
    BadcaseStore,
    ReportStore,
    SessionStateStore,
    TaskStateStore,
    TraceRecorder,
)
from ananhu_agent.workflow.contracts import RunRequest


class _CanaryReasoningGateway:
    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            output={
                "intent": "payment_calculation",
                "confidence": 0.96,
                "slots": {
                    "province": "四川省",
                    "disability_grade": "十级",
                    "monthly_wage": 6000,
                },
                "missing_slots": [],
                "is_composite": False,
            },
            provider="provider",
            model="provider-model",
            profile=request.profile,
            usage=ModelUsage(
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
                usage_source="provider",
                reported=True,
            ),
            reasoning_content="CANARY_REASONING",
        )


def test_reasoning_canary_never_enters_runtime_persistence(tmp_path) -> None:
    runtime = create_default_runtime(tmp_path)
    runtime.intent_agent.model_gateway = ObservableModelGateway(
        _CanaryReasoningGateway(),
        events=NoOpRunEventSink(),
        sanitizer=TransientSanitizer(),
    )

    result = asyncio.run(runtime.invoke(RunRequest(
        run_id="run_reasoning_security",
        request_id="req_reasoning_security",
        session_id="sess_reasoning_security",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
        created_at="2026-07-10T00:00:00+08:00",
    )))

    persisted = {
        "workflow_result": result.model_dump(mode="json"),
        "task_states": TaskStateStore(tmp_path / "task_states.jsonl").read_all(),
        "run_reports": ReportStore(tmp_path / "run_reports.jsonl").read_all(),
        "session_states": SessionStateStore(tmp_path / "session_states.jsonl").read_all(),
        "badcases": BadcaseStore(tmp_path / "badcases.jsonl").read_all(),
        "trace": TraceRecorder(tmp_path / "traces.jsonl").read_all(),
    }
    serialized = json.dumps(persisted, ensure_ascii=False)

    assert "CANARY_REASONING" not in serialized


def test_nested_secret_sanitizer_masks_keys_and_configured_values() -> None:
    canary = secrets.token_urlsafe(24)
    value = {
        "headers": {"Authorization": f"Bearer {canary}"},
        "items": [{"token": canary}],
        "home": "/home/xukai",
    }

    clean = sanitize(value, configured_secrets={canary})

    assert canary not in json.dumps(clean)
    assert clean["home"] == "/home/xukai"


def test_sanitizer_masks_query_headers_and_case_variants() -> None:
    canary = secrets.token_urlsafe(24)
    value = {
        "Api_Key": canary,
        "url": f"https://provider.example/v1?access_token={canary}&page=1",
        "headers": {"X-TOKEN": canary},
    }

    clean = sanitize(value)
    serialized = json.dumps(clean)

    assert canary not in serialized
    assert "page=1" in clean["url"]
    assert "access_token=%2A%2A%2A" in clean["url"]


def test_sanitizer_masks_url_userinfo_credentials() -> None:
    canary = secrets.token_urlsafe(24)

    clean = sanitize({"endpoint": f"https://proxy:{canary}@provider.example/v1"})

    assert canary not in json.dumps(clean)
    assert clean["endpoint"] == "https://***@provider.example/v1"


def test_sanitized_provider_error_never_contains_canary() -> None:
    canary = secrets.token_urlsafe(24)
    error_payload = {
        "error": {"message": f"provider rejected Bearer {canary}"},
        "request_headers": {"cookie": canary},
    }

    clean = sanitize(error_payload, configured_secrets={canary})

    assert canary not in json.dumps(clean)


def test_non_sensitive_environment_values_are_preserved() -> None:
    clean = sanitize({"HOME": "/home/xukai", "LANG": "zh_CN.UTF-8"})

    assert clean == {"HOME": "/home/xukai", "LANG": "zh_CN.UTF-8"}


@pytest.mark.asyncio
async def test_runtime_random_canary_never_leaks_to_screen_logs_or_artifacts(
    tmp_path: Path, caplog
) -> None:
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    canary = secrets.token_urlsafe(32)

    class CanaryRuntime:
        def __init__(self) -> None:
            self.events = asyncio.Queue()

        async def invoke(self, request):
            await self.events.put(NodeStartedEvent(
                run_id=request.run_id,
                request_id=request.request_id,
                session_id=request.session_id,
                node_id="understand",
                sequence_no=1,
                public_payload={"phase": "understand", "input_summary": {"query": "safe"}},
                transient_payload=RunTransientPayload(prompt=canary),
            ))
            await self.events.put(ModelFinishedEvent(
                run_id=request.run_id,
                request_id=request.request_id,
                session_id=request.session_id,
                node_id="understand",
                sequence_no=2,
                public_payload=ModelFinishedPayload(
                    profile="intent_fast",
                    provider="provider",
                    model="model",
                    output_summary={
                        "tool_result": {"token": canary},
                        "endpoint": f"https://user:{canary}@provider.example/v1",
                    },
                ),
                transient_payload=RunTransientPayload(reasoning_content=canary),
            ))
            await self.events.put(RunFinishedEvent(
                run_id=request.run_id,
                request_id=request.request_id,
                session_id=request.session_id,
                sequence_no=3,
                public_payload={"status": "failed", "stop_reason": "capability_failed"},
            ))
            raise RuntimeError(f"provider error token={canary}")

    runtime = CanaryRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("x", "enter")
        await pilot.pause()
        await pilot.pause()
        if app._running_task is not None:
            await app._running_task
        screen_export = app.export_screenshot()

    sanitized = sanitize({
        "prompt": canary,
        "secret": SecretStr(canary),
        "headers": {"Authorization": f"Bearer {canary}"},
        "url": f"https://user:{canary}@provider.example/v1?access_token={canary}",
        "tool_result": {"token": canary},
        "error": RuntimeError(f"provider error token={canary}"),
    }, configured_secrets={canary})
    persisted = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    git_scan = subprocess.run(
        ["git", "grep", "-n", "--fixed-strings", canary, "--"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert canary not in screen_export
    assert canary not in json.dumps(sanitized, ensure_ascii=False)
    assert canary not in caplog.text
    assert canary not in persisted
    assert git_scan.returncode == 1
