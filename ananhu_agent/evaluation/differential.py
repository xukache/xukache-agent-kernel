from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ananhu_agent.schemas import now_cn
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

        native_result = await self.native_runtime.invoke(request)
        langgraph_result = await self.langgraph_runtime.invoke(request)
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
        """执行一批 eval case 并写入单个结构化差分 artifact。"""

        comparisons = []
        batch_id = uuid4().hex[:12]
        for index, case in enumerate(cases, start=1):
            request = RunRequest(
                run_id=f"run_diff_{batch_id}_{index}",
                request_id=f"req_diff_{batch_id}_{index}",
                session_id=f"runtime-differential-{batch_id}-{index}",
                turn_id=index,
                user_query=case["query"],
                created_at=now_cn(),
            )
            comparisons.append(asyncio.run(self.compare(request, case_id=case["id"])))

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
        return report


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
