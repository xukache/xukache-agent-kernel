"""真实对话证据的结构化记录、隔离上下文和脱敏写入。

该模块只服务于测试与验收，不属于 Agent Kernel 公共 API。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypeAliasType

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue = TypeAliasType(
    "JsonValue",
    JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"],
)
JsonObject = TypeAliasType("JsonObject", dict[str, JsonValue])

_TEST_ID_PATTERN = re.compile(r"^RD-\d{3}$")
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|authorization|password|secret|token)"
)
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_ -]?key|authorization|password|secret|token)\b"
    r"(\s*[:=]\s*)[^\s,;]+"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
_OPENAI_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]+")
DEFAULT_EVIDENCE_ROOT = Path("artifacts/real-dialogue")


class EvidenceStatus(str, Enum):
    """真实对话验收允许的四种状态。"""

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT RUN"


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    """为一次场景运行提供互相隔离的标识。"""

    test_id: str
    run_id: str
    scope: str


class FailureDetails(BaseModel):
    """失败或阻塞时追加的可复现信息。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    expected: JsonValue
    actual: JsonValue
    failure_stage: str
    reproducible_command: str


class DialogueEvidence(BaseModel):
    """符合第四章最小字段要求的单次真实对话证据。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    test_id: str
    run_id: str
    scope: str
    model_id: str
    provider: str
    raw_dialogue_input: str | list[str]
    expected_structured_assertions: JsonObject
    actual_output_summary: JsonObject
    events: list[JsonObject]
    usage: JsonObject
    latency: float = Field(ge=0)
    error_type: str | None
    retry_count: int = Field(ge=0)
    status: EvidenceStatus
    recorded_at: datetime
    failure: FailureDetails | None = None


def create_evidence_context(test_id: str) -> EvidenceContext:
    """为每次场景执行生成独立的 run_id 和 Memory scope。"""
    if not _TEST_ID_PATTERN.fullmatch(test_id):
        raise ValueError(f"invalid real dialogue test_id: {test_id}")

    return EvidenceContext(
        test_id=test_id,
        run_id=f"run-{uuid4().hex}",
        scope=f"scope-{uuid4().hex}",
    )


def evidence_root() -> Path:
    """读取证据工件目录；默认目录被 Git 忽略，避免提交运行产物。"""
    configured_root = os.getenv("ANANHU_REAL_DIALOGUE_EVIDENCE_DIR")
    return Path(configured_root) if configured_root else DEFAULT_EVIDENCE_ROOT


def redact_sensitive_data(value: JsonValue) -> JsonValue:
    """递归移除证据中的凭证和常见密钥文本。"""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if _SECRET_KEY_PATTERN.search(key)
            else redact_sensitive_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    if isinstance(value, str):
        redacted = _SECRET_ASSIGNMENT_PATTERN.sub(
            r"\1\2[REDACTED]",
            value,
        )
        redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
        return _OPENAI_KEY_PATTERN.sub("[REDACTED]", redacted)
    return value


class EvidenceRecorder:
    """把单次证据以稳定 JSON 写入受控工件目录。"""

    def __init__(self, root: Path) -> None:
        self._root = root

    def write(
        self,
        *,
        context: EvidenceContext,
        model_id: str,
        provider: str,
        raw_dialogue_input: str | list[str],
        expected_structured_assertions: JsonObject,
        actual_output_summary: JsonObject,
        events: list[JsonObject],
        usage: JsonObject,
        latency: float,
        error_type: str | None,
        retry_count: int,
        status: EvidenceStatus,
        failure: FailureDetails | None = None,
    ) -> Path:
        if status in {EvidenceStatus.FAIL, EvidenceStatus.BLOCKED} and failure is None:
            raise ValueError("failure details are required for FAIL or BLOCKED evidence")

        evidence = DialogueEvidence(
            test_id=context.test_id,
            run_id=context.run_id,
            scope=context.scope,
            model_id=model_id,
            provider=provider,
            raw_dialogue_input=redact_sensitive_data(raw_dialogue_input),
            expected_structured_assertions=redact_sensitive_data(
                expected_structured_assertions
            ),
            actual_output_summary=redact_sensitive_data(actual_output_summary),
            events=redact_sensitive_data(events),
            usage=redact_sensitive_data(usage),
            latency=latency,
            error_type=error_type,
            retry_count=retry_count,
            status=status,
            recorded_at=datetime.now(timezone.utc),
            failure=(
                FailureDetails.model_validate(
                    redact_sensitive_data(failure.model_dump(mode="json"))
                )
                if failure is not None
                else None
            ),
        )

        destination = self._root / context.test_id / f"{context.run_id}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                evidence.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
        return destination
