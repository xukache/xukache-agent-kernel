from __future__ import annotations

import asyncio
import json
from time import perf_counter
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ananhu_agent.evaluation.runner import (
    _case_record,
    _evaluation_kind,
    _exception_failure_reasons,
    _failed_case_record,
    _failure_reasons,
    summarize_case_records,
)
from ananhu_agent.schemas import now_cn
from ananhu_agent.storage.jsonl_store import JsonlStore
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.workflow.contracts import RunRequest, WorkflowRuntime


class DifferentialMismatch(BaseModel):
    """Native 与 LangGraph 在一个禁止差异字段上的值。"""

    path: str
    native: Any = None
    langgraph: Any = None


class DifferentialComparison(BaseModel):
    """单个 eval case 的双运行时比较结果。"""

    case_id: str
    request_id: str
    equivalent: bool
    compared_trace_events: int
    mismatches: list[DifferentialMismatch] = Field(default_factory=list)


class DifferentialReport(BaseModel):
    """可持久化的双运行时差分验收产物。"""

    schema_version: str = "runtime-differential.v1"
    total: int
    equivalent: int
    different: int
    cases: list[DifferentialComparison]
    created_at: str = Field(default_factory=now_cn)


class RuntimeDifferentialRunner:
    """只读取项目 Runtime 端口、WorkflowResult 和 TraceEvent 的差分执行器。"""

    def __init__(
        self,
        native_runtime: WorkflowRuntime,
        langgraph_runtime: WorkflowRuntime,
        native_trace: TraceRecorder,
        langgraph_trace: TraceRecorder,
        artifact_path: Path,
    ) -> None:
        self.native_runtime = native_runtime
        self.langgraph_runtime = langgraph_runtime
        self.native_trace = native_trace
        self.langgraph_trace = langgraph_trace
        self.artifact_path = artifact_path

    async def compare(self, request: RunRequest, case_id: str) -> DifferentialComparison:
        """使用同一请求运行两种 Runtime，并比较业务结果与项目 trace。"""

        comparison, _, _, _, _, _, _ = await self._compare_with_results(
            request,
            case_id,
        )
        return comparison

    async def _compare_with_results(
        self,
        request: RunRequest,
        case_id: str,
    ) -> tuple[
        DifferentialComparison,
        Any,
        Any,
        Exception | None,
        Exception | None,
        float,
        float,
    ]:
        native_result, native_error, native_latency_ms = await _invoke_captured(
            self.native_runtime,
            request,
        )
        langgraph_result, langgraph_error, langgraph_latency_ms = await _invoke_captured(
            self.langgraph_runtime,
            request,
        )
        if native_error or langgraph_error:
            native_events = _events_for_request(self.native_trace, request.request_id)
            langgraph_events = _events_for_request(
                self.langgraph_trace,
                request.request_id,
            )
            mismatches: list[DifferentialMismatch] = []
            if native_error:
                mismatches.append(
                    DifferentialMismatch(
                        path="runtime.native_error",
                        native=type(native_error).__name__,
                    )
                )
            if langgraph_error:
                mismatches.append(
                    DifferentialMismatch(
                        path="runtime.langgraph_error",
                        langgraph=type(langgraph_error).__name__,
                    )
                )
            comparison = DifferentialComparison(
                case_id=case_id,
                request_id=request.request_id,
                equivalent=False,
                compared_trace_events=min(
                    len(native_events),
                    len(langgraph_events),
                ),
                mismatches=mismatches,
            )
            return (
                comparison,
                native_result,
                langgraph_result,
                native_error,
                langgraph_error,
                native_latency_ms,
                langgraph_latency_ms,
            )
        return (
            self._compare_results(
                request,
                case_id,
                native_result,
                langgraph_result,
            ),
            native_result,
            langgraph_result,
            None,
            None,
            native_latency_ms,
            langgraph_latency_ms,
        )

    def _compare_results(
        self,
        request: RunRequest,
        case_id: str,
        native_result: Any,
        langgraph_result: Any,
    ) -> DifferentialComparison:
        mismatches = _diff_values(
            _normalize_result(native_result.model_dump()),
            _normalize_result(langgraph_result.model_dump()),
            path="result",
        )

        native_events = _events_for_request(self.native_trace, request.request_id)
        langgraph_events = _events_for_request(self.langgraph_trace, request.request_id)
        mismatches.extend(_diff_values(native_events, langgraph_events, path="trace"))
        return DifferentialComparison(
            case_id=case_id,
            request_id=request.request_id,
            equivalent=not mismatches,
            compared_trace_events=min(len(native_events), len(langgraph_events)),
            mismatches=mismatches,
        )

    def run_cases(self, cases: list[dict[str, Any]]) -> DifferentialReport:
        """执行双运行时 eval，并同时写入差分与逐 case 评测产物。"""

        comparisons = []
        native_case_records: list[dict[str, Any]] = []
        langgraph_case_records: list[dict[str, Any]] = []
        batch_id = uuid4().hex[:12]
        for index, case in enumerate(cases, start=1):
            request = RunRequest(
                run_id=f"run_diff_{batch_id}_{index}",
                request_id=f"req_diff_{batch_id}_{index}",
                session_id=f"runtime-differential-{batch_id}-{index}",
                turn_id=index,
                user_query=case["query"],
                case_id=case.get("case_id"),
                message_id=case.get("message_id"),
                trusted_jurisdiction=case.get("trusted_jurisdiction", {}),
                created_at=now_cn(),
            )
            (
                comparison,
                native_result,
                langgraph_result,
                native_error,
                langgraph_error,
                native_latency_ms,
                langgraph_latency_ms,
            ) = asyncio.run(
                self._compare_with_results(request, case_id=case["id"])
            )
            native_events = _events_for_request(self.native_trace, request.request_id)
            langgraph_events = _events_for_request(
                self.langgraph_trace,
                request.request_id,
            )
            native_case_records.append(_runtime_case_record(
                case,
                native_result,
                native_error,
                native_events,
                native_latency_ms,
            ))
            langgraph_case_records.append(_runtime_case_record(
                case,
                langgraph_result,
                langgraph_error,
                langgraph_events,
                langgraph_latency_ms,
            ))
            native_failures = native_case_records[-1]["failure_reasons"]
            langgraph_failures = langgraph_case_records[-1]["failure_reasons"]
            _append_eval_badcase(self.native_trace, case, native_failures)
            _append_eval_badcase(self.langgraph_trace, case, langgraph_failures)
            comparisons.append(comparison)

        report = DifferentialReport(
            total=len(comparisons),
            equivalent=sum(comparison.equivalent for comparison in comparisons),
            different=sum(not comparison.equivalent for comparison in comparisons),
            cases=comparisons,
        )
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_path.write_text(
            json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.artifact_path.with_name("evaluation.json").write_text(
            json.dumps(
                {
                    "schema_version": "evaluation.v1",
                    "evaluation_kind": _evaluation_kind(
                        cases,
                        Path("real_smoke_cases.jsonl"),
                    ),
                    "runtime": "both",
                    "runtimes": {
                        "native": {
                            "summary": summarize_case_records(native_case_records),
                            "cases": native_case_records,
                        },
                        "langgraph": {
                            "summary": summarize_case_records(langgraph_case_records),
                            "cases": langgraph_case_records,
                        },
                    },
                    "differential": report.model_dump(mode="json"),
                    "created_at": now_cn(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return report


def _answer_passed(result: Any, case: dict[str, Any]) -> bool:
    answer = result.final_answer or ""
    return all(fragment in answer for fragment in case.get("expect_contains", []))


def _runtime_case_record(
    case: dict[str, Any],
    result: Any,
    error: Exception | None,
    trace_events: list[dict[str, Any]],
    latency_ms: float,
) -> dict[str, Any]:
    if error is not None or result is None or result.final_state is None:
        failure_reasons = _exception_failure_reasons(trace_events, error or RuntimeError(
            "runtime result missing final_state"
        ))
        return _failed_case_record(
            case,
            trace_events=trace_events,
            latency_ms=latency_ms,
            failure_reasons=failure_reasons,
            error=error or RuntimeError("runtime result missing final_state"),
        )
    answer_passed = _answer_passed(result, case)
    return _case_record(
        case,
        result,
        result.final_state,
        trace_events=trace_events,
        latency_ms=latency_ms,
        failure_reasons=_failure_reasons(
            case,
            result.final_state,
            answer_passed=answer_passed,
        ),
        answer_passed=answer_passed,
    )


async def _invoke_captured(
    runtime: WorkflowRuntime,
    request: RunRequest,
) -> tuple[Any, Exception | None, float]:
    started_at = perf_counter()
    try:
        return (
            await runtime.invoke(request),
            None,
            round((perf_counter() - started_at) * 1000, 2),
        )
    except Exception as exc:
        return (
            None,
            exc,
            round((perf_counter() - started_at) * 1000, 2),
        )


def _append_eval_badcase(
    trace_recorder: TraceRecorder,
    case: dict[str, Any],
    failure_reasons: list[str],
) -> None:
    """把双运行时评测失败追加到对应 runtime 的 badcase 证据。"""

    if not failure_reasons:
        return
    JsonlStore(trace_recorder.store.path.parent / "badcases.jsonl").append(
        {
            "case_id": case["id"],
            "query": case["query"],
            "issue_type": "eval_failed",
            "expected_answer": case.get("expect_contains", []),
            "failure_reasons": failure_reasons,
        }
    )


def _normalize_result(value: Any) -> Any:
    """移除结果中的时间字段；其余业务状态、证据和调用字段必须一致。"""

    normalized = _remove_keys(value, {"latency_ms"})
    normalized.pop("created_at", None)
    return normalized


def _events_for_request(recorder: TraceRecorder, request_id: str) -> list[dict[str, Any]]:
    events = [event for event in recorder.read_all() if event["request_id"] == request_id]
    normalized = []
    for event in events:
        normalized_event = _remove_keys(event, {"latency_ms"})
        for key in ("id", "runtime_name", "runtime_version", "created_at"):
            normalized_event.pop(key, None)
        normalized.append(normalized_event)
    # 节点内部事件时序是允许差异；规范化后比较业务事件多重集合。
    return sorted(normalized, key=lambda event: json.dumps(event, ensure_ascii=False, sort_keys=True))


def _remove_keys(value: Any, ignored_keys: set[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _remove_keys(item, ignored_keys)
            for key, item in value.items()
            if key not in ignored_keys
        }
    if isinstance(value, list):
        return [_remove_keys(item, ignored_keys) for item in value]
    return value


def _diff_values(native: Any, langgraph: Any, path: str) -> list[DifferentialMismatch]:
    if type(native) is not type(langgraph):
        return [DifferentialMismatch(path=path, native=native, langgraph=langgraph)]
    if isinstance(native, dict):
        mismatches = []
        for key in sorted(set(native) | set(langgraph)):
            child_path = f"{path}.{key}"
            if key not in native or key not in langgraph:
                mismatches.append(
                    DifferentialMismatch(
                        path=child_path,
                        native=native.get(key),
                        langgraph=langgraph.get(key),
                    )
                )
                continue
            mismatches.extend(_diff_values(native[key], langgraph[key], child_path))
        return mismatches
    if isinstance(native, list):
        if len(native) != len(langgraph):
            return [DifferentialMismatch(path=path, native=native, langgraph=langgraph)]
        mismatches = []
        for index, (native_item, langgraph_item) in enumerate(zip(native, langgraph, strict=True)):
            mismatches.extend(
                _diff_values(native_item, langgraph_item, f"{path}[{index}]")
            )
        return mismatches
    if native != langgraph:
        return [DifferentialMismatch(path=path, native=native, langgraph=langgraph)]
    return []
