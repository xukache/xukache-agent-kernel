"""真实对话证据支持层的确定性测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.real_dialogue_evidence import (
    EvidenceRecorder,
    EvidenceStatus,
    create_evidence_context,
    evidence_root,
    redact_sensitive_data,
)


def test_context_generates_isolated_run_id_and_scope() -> None:
    first = create_evidence_context("RD-001")
    second = create_evidence_context("RD-001")

    assert first.test_id == "RD-001"
    assert first.run_id != second.run_id
    assert first.scope != second.scope


def test_evidence_root_has_a_local_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANANHU_REAL_DIALOGUE_EVIDENCE_DIR", raising=False)

    assert evidence_root().as_posix() == "artifacts/real-dialogue"


def test_recorder_writes_minimum_evidence_and_redacts_secrets(
    tmp_path: Path,
) -> None:
    recorder = EvidenceRecorder(tmp_path)
    context = create_evidence_context("RD-001")

    path = recorder.write(
        context=context,
        model_id="test-model",
        provider="test-provider",
        raw_dialogue_input="请计算 18 + 24。",
        expected_structured_assertions={"result": 42},
        actual_output_summary={"result": 42},
        events=[{"type": "completed", "api_key": "sk-live-secret"}],
        usage={"input_tokens": 10, "output_tokens": 4},
        latency=0.42,
        error_type=None,
        retry_count=0,
        status=EvidenceStatus.PASS,
    )

    document = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / "RD-001" / f"{context.run_id}.json"
    assert document["status"] == "PASS"
    assert document["run_id"] == context.run_id
    assert document["scope"] == context.scope
    assert document["events"][0]["api_key"] == "[REDACTED]"


def test_failure_evidence_requires_failure_details(tmp_path: Path) -> None:
    recorder = EvidenceRecorder(tmp_path)
    context = create_evidence_context("RD-001")

    with pytest.raises(ValueError, match="failure"):
        recorder.write(
            context=context,
            model_id="test-model",
            provider="test-provider",
            raw_dialogue_input="请计算 18 + 24。",
            expected_structured_assertions={"result": 42},
            actual_output_summary={"result": 41},
            events=[],
            usage={},
            latency=0.42,
            error_type="assertion",
            retry_count=0,
            status=EvidenceStatus.FAIL,
        )


def test_redact_sensitive_data_covers_nested_values() -> None:
    value = {
        "authorization": "Bearer abc",
        "nested": [{"password": "secret"}, {"message": "api_key=hidden"}],
    }

    assert redact_sensitive_data(value) == {
        "authorization": "[REDACTED]",
        "nested": [{"password": "[REDACTED]"}, {"message": "api_key=[REDACTED]"}],
    }
