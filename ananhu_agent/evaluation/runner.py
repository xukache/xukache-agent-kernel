from __future__ import annotations

import json
import asyncio
from math import ceil
from statistics import median
from time import perf_counter
from pathlib import Path
from typing import Any

from ananhu_agent.evaluation.metrics import (
    score_case,
    score_capability_success,
    score_citations,
    score_intent,
    score_safety,
    score_slots,
)
from ananhu_agent.orchestrator.badcase_rules import detect_badcase_issues
from ananhu_agent.storage.jsonl_store import JsonlStore
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.schemas import now_cn
from ananhu_agent.workflow.contracts import RunRequest, WorkflowRuntime


class EvalRunner:
    """本地评测执行器，负责回放 case、汇总指标并沉淀 badcase。"""

    def __init__(
        self,
        runtime: WorkflowRuntime,
        output_dir: Path,
        *,
        runtime_name: str | None = None,
    ) -> None:
        self.runtime = runtime
        self.output_dir = output_dir
        self.runtime_name = runtime_name or _runtime_name(runtime)

    def run(self, cases_path: Path) -> dict[str, Any]:
        """运行 JSONL eval cases，并写入汇总指标与逐 case 评测产物。"""

        rows = [
            json.loads(line)
            for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        badcases = JsonlStore(self.output_dir / "badcases.jsonl")
        trace_recorder = TraceRecorder(self.output_dir / "traces.jsonl")
        passed = 0
        intent_passed = 0
        intent_total = 0
        slot_passed = 0
        slot_total = 0
        citation_passed = 0
        citation_total = 0
        capability_passed = 0
        capability_total = 0
        safety_passed = 0
        latency_values: list[float] = []
        case_records: list[dict[str, Any]] = []

        for index, case in enumerate(rows, start=1):
            started_at = perf_counter()
            request = RunRequest(
                run_id=f"run_eval_{index}",
                request_id=f"req_eval_{index}",
                session_id="eval",
                turn_id=index,
                user_query=case["query"],
                trusted_jurisdiction=case.get("trusted_jurisdiction", {}),
                created_at=now_cn(),
            )
            try:
                result = asyncio.run(self.runtime.invoke(request))
            except Exception as exc:
                latency_ms = round((perf_counter() - started_at) * 1000, 2)
                trace_events = [
                    event
                    for event in trace_recorder.read_all()
                    if event.get("request_id") == request.request_id
                ]
                failure_reasons = _exception_failure_reasons(trace_events, exc)
                case_records.append(
                    _failed_case_record(
                        case,
                        trace_events=trace_events,
                        latency_ms=latency_ms,
                        failure_reasons=failure_reasons,
                        error=exc,
                    )
                )
                badcases.append(
                    {
                        "case_id": case["id"],
                        "query": case["query"],
                        "issue_type": "runtime_or_recovery_error",
                        "expected_answer": case.get("expect_contains", []),
                        "failure_reasons": failure_reasons,
                        "error_type": type(exc).__name__,
                    }
                )
                continue
            state = result.final_state
            if state is None:
                raise RuntimeError("WorkflowRuntime result missing final_state for eval")
            latency_ms = round((perf_counter() - started_at) * 1000, 2)
            latency_values.append(latency_ms)

            if "expected_intent" in case:
                intent_total += 1
                intent_passed += int(score_intent(state, case["expected_intent"]))

            if "expected_slots" in case:
                slot_total += 1
                slot_passed += int(score_slots(state, case["expected_slots"]))

            if "expected_citations" in case:
                citation_total += 1
                citation_passed += int(score_citations(state, case["expected_citations"]))

            if state.capability_results:
                capability_total += 1
                capability_passed += int(score_capability_success(state))

            safety_ok = score_safety(state)
            safety_passed += int(safety_ok)
            ok = score_case(result.final_answer or "", case.get("expect_contains", []))
            trace_events = [
                event
                for event in trace_recorder.read_all()
                if event.get("request_id") == request_id_for_case(result)
            ]
            failure_reasons = _failure_reasons(
                case,
                state,
                answer_passed=ok,
            )
            case_records.append(
                _case_record(
                    case,
                    result,
                    state,
                    trace_events=trace_events,
                    latency_ms=latency_ms,
                    failure_reasons=failure_reasons,
                    answer_passed=ok,
                )
            )
            if ok:
                passed += 1
            if failure_reasons:
                badcases.append(
                    {
                        "case_id": case["id"],
                        "query": case["query"],
                        "answer": result.final_answer,
                        "issue_type": "eval_failed",
                        "expected_answer": case.get("expect_contains", []),
                        "failure_reasons": failure_reasons,
                    }
                )

        metrics = {
            "total": len(rows),
            "passed": passed,
            "failed": len(rows) - passed,
            "intent_accuracy": _rate(intent_passed, intent_total),
            "slot_accuracy": _rate(slot_passed, slot_total),
            "citation_accuracy": _rate(citation_passed, citation_total),
            "capability_success_rate": _rate(capability_passed, capability_total),
            "unsafe_expression_rate": _rate(len(rows) - safety_passed, len(rows)),
            "safety_pass_rate": _rate(safety_passed, len(rows)),
            "latency_ms_avg": round(sum(latency_values) / len(latency_values), 2)
            if latency_values
            else 0.0,
            "latency_ms_p50": _percentile(latency_values, 0.50),
            "latency_ms_p95": _percentile(latency_values, 0.95),
        }
        metrics.update(_usage_metrics(case_records))
        metrics["badcase_count"] = sum(
            1 for record in case_records if record["failure_reasons"]
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        evaluation_kind = _evaluation_kind(rows, cases_path)
        (self.output_dir / "evaluation.json").write_text(
            json.dumps(
                {
                    "schema_version": "evaluation.v1",
                    "evaluation_kind": evaluation_kind,
                    "runtime": self.runtime_name,
                    "dataset": {
                        "path": str(cases_path),
                        "case_count": len(rows),
                    },
                    "summary": metrics,
                    "cases": case_records,
                    "created_at": now_cn(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return metrics


def _rate(passed: int, total: int) -> float | None:
    """无适用 case 时返回 None，避免把未覆盖误报成 0 分。"""

    if total == 0:
        return None
    return passed / total


def request_id_for_case(result: Any) -> str:
    """从框架中立结果取 trace 关联 ID，避免 EvalRunner 依赖 Runtime 内部实现。"""

    return result.request_id


def _runtime_name(runtime: WorkflowRuntime) -> str:
    name = type(runtime).__name__.lower()
    return "native" if "native" in name else "langgraph"


def _evaluation_kind(rows: list[dict[str, Any]], cases_path: Path) -> str:
    declared = {row.get("evaluation_kind") for row in rows if row.get("evaluation_kind")}
    if len(declared) == 1:
        return next(iter(declared))
    return "real_smoke" if cases_path.name == "real_smoke_cases.jsonl" else "offline"


def _failure_reasons(
    case: dict[str, Any],
    state: Any,
    *,
    answer_passed: bool,
) -> list[str]:
    """将机制断言和运行时自动候选合并为可定位的失败分类。"""

    reasons = detect_badcase_issues(state)
    if case.get("expected_intent") and not score_intent(state, case["expected_intent"]):
        reasons.append("intent_mismatch")
    if case.get("expected_slots") and not score_slots(state, case["expected_slots"]):
        reasons.append("slot_mismatch")
    if case.get("expected_citations") and not score_citations(
        state, case["expected_citations"]
    ):
        reasons.append("citation_error")
    if not answer_passed:
        reasons.append("response_inconsistency")
    return list(dict.fromkeys(reasons))


def _case_record(
    case: dict[str, Any],
    result: Any,
    state: Any,
    *,
    trace_events: list[dict[str, Any]],
    latency_ms: float,
    failure_reasons: list[str],
    answer_passed: bool,
) -> dict[str, Any]:
    model_calls = _model_calls(trace_events)
    evidence_ids = [
        evidence.get("evidence_id")
        for evidence in state.evidence
        if evidence.get("evidence_id")
    ]
    citation_titles = [
        evidence.get("citation", {}).get("title", "")
        for evidence in state.evidence
    ]
    capabilities = [
        {
            "capability_name": result_row.get("capability_name"),
            "status": result_row.get("status"),
            "error": result_row.get("error"),
            "evidence_count": len(result_row.get("output", {}).get("evidences", [])),
        }
        for result_row in state.capability_results
    ]
    usage = _aggregate_usage([call["usage"] for call in model_calls])
    return {
        "case_id": case["id"],
        "category": case.get("category"),
        "status": result.status.value,
        "stop_reason": result.stop_reason.value if result.stop_reason else None,
        "predicted_intent": (
            state.intent_result.get("intent") if state.intent_result else None
        ),
        "intent": {
            "expected": case.get("expected_intent"),
            "actual": (
                state.intent_result.get("intent") if state.intent_result else None
            ),
            "passed": (
                score_intent(state, case["expected_intent"])
                if case.get("expected_intent")
                else None
            ),
        },
        "slots": {
            "expected": case.get("expected_slots", {}),
            "actual": state.case_facts,
            "passed": (
                score_slots(state, case["expected_slots"])
                if case.get("expected_slots")
                else None
            ),
        },
        "model_calls": model_calls,
        "retrieval": {
            "capabilities": capabilities,
            "evidence_count": len(state.evidence),
            "evidence_ids": evidence_ids,
            "citation_titles": citation_titles,
        },
        "citation": {
            "expected": case.get("expected_citations", []),
            "actual_titles": citation_titles,
            "passed": (
                score_citations(state, case["expected_citations"])
                if case.get("expected_citations")
                else None
            ),
        },
        "safety": state.safety_result or {},
        "usage": usage,
        "latency_ms": latency_ms,
        "answer_present": bool((result.final_answer or "").strip()),
        "answer_passed": answer_passed,
        "failure_reasons": failure_reasons,
    }


def _model_calls(trace_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for event in trace_events:
        if event.get("event_type") not in {"model_finished", "model_failed"}:
            continue
        payload = event.get("payload", {})
        if event.get("event_type") == "model_failed":
            calls.append(
                {
                    "profile": payload.get("model_profile"),
                    "provider": payload.get("provider"),
                    "model": None,
                    "finish_reason": None,
                    "error_code": payload.get("error_code"),
                    "usage": {},
                    "latency_ms": payload.get("latency_ms") or 0,
                }
            )
            continue
        model_result = payload.get("model_result", payload)
        usage = model_result.get("usage") or {}
        calls.append(
            {
                "profile": model_result.get("profile") or payload.get("model_profile"),
                "provider": model_result.get("provider"),
                "model": model_result.get("model"),
                "finish_reason": model_result.get("finish_reason"),
                "usage": usage,
                "latency_ms": model_result.get("latency_ms")
                or payload.get("latency_ms")
                or 0,
            }
        )
    return calls


def _exception_failure_reasons(
    trace_events: list[dict[str, Any]],
    error: Exception,
) -> list[str]:
    reasons = ["runtime_or_recovery_error"]
    error_codes = [
        event.get("payload", {}).get("error_code")
        for event in trace_events
        if event.get("event_type") == "model_failed"
    ]
    error_code = next((code for code in error_codes if code), None)
    if error_code:
        reasons.append(str(error_code))
    elif type(error).__name__ == "ModelGatewayError":
        code = getattr(error, "code", None)
        reasons.append(getattr(code, "value", None) or "model_provider_error")
    else:
        reasons.append(type(error).__name__)
    return list(dict.fromkeys(reasons))


def _failed_case_record(
    case: dict[str, Any],
    *,
    trace_events: list[dict[str, Any]],
    latency_ms: float,
    failure_reasons: list[str],
    error: Exception,
) -> dict[str, Any]:
    return {
        "case_id": case["id"],
        "category": case.get("category"),
        "status": "failed",
        "stop_reason": "runtime_or_recovery_error",
        "predicted_intent": None,
        "intent": {
            "expected": case.get("expected_intent"),
            "actual": None,
            "passed": False if case.get("expected_intent") else None,
        },
        "slots": {
            "expected": case.get("expected_slots", {}),
            "actual": {},
            "passed": False if case.get("expected_slots") else None,
        },
        "model_calls": _model_calls(trace_events),
        "retrieval": {
            "capabilities": [],
            "evidence_count": 0,
            "evidence_ids": [],
            "citation_titles": [],
        },
        "citation": {
            "expected": case.get("expected_citations", []),
            "actual_titles": [],
            "passed": False if case.get("expected_citations") else None,
        },
        "safety": {},
        "usage": _aggregate_usage([]),
        "latency_ms": latency_ms,
        "answer_present": False,
        "answer_passed": False,
        "error_type": type(error).__name__,
        "failure_reasons": failure_reasons,
    }


def _aggregate_usage(usages: list[dict[str, Any]]) -> dict[str, Any]:
    if not usages:
        return {
            "usage_source": "unknown",
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
        }
    sources = {usage.get("usage_source", "unknown") for usage in usages}
    return {
        "usage_source": next(iter(sources)) if len(sources) == 1 else "mixed",
        "input_tokens": sum(usage.get("input_tokens", 0) for usage in usages),
        "output_tokens": sum(usage.get("output_tokens", 0) for usage in usages),
        "cache_tokens": sum(usage.get("cache_tokens", 0) for usage in usages),
        "total_tokens": sum(usage.get("total_tokens", 0) for usage in usages),
        "calls": len(usages),
    }


def _usage_metrics(case_records: list[dict[str, Any]]) -> dict[str, Any]:
    usages = [record["usage"] for record in case_records]
    aggregate = _aggregate_usage(usages)
    profiles = sorted({
        call["profile"]
        for record in case_records
        for call in record["model_calls"]
        if call.get("profile")
    })
    providers = sorted({
        call["provider"]
        for record in case_records
        for call in record["model_calls"]
        if call.get("provider")
    })
    models = sorted({
        call["model"]
        for record in case_records
        for call in record["model_calls"]
        if call.get("model")
    })
    return {
        "model_profiles": profiles,
        "providers": providers,
        "models": models,
        "usage_source": aggregate["usage_source"],
        "input_tokens": aggregate["input_tokens"],
        "output_tokens": aggregate["output_tokens"],
        "cache_tokens": aggregate["cache_tokens"],
        "total_tokens": aggregate["total_tokens"],
        "model_calls": aggregate["calls"],
    }


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, ceil(len(ordered) * quantile) - 1))
    return round(ordered[index], 2)


def summarize_case_records(case_records: list[dict[str, Any]]) -> dict[str, Any]:
    """从逐 case 产物汇总双运行时和单运行时都可复用的机制指标。"""

    total = len(case_records)
    intent_records = [
        record for record in case_records if record["intent"]["passed"] is not None
    ]
    slot_records = [
        record for record in case_records if record["slots"]["passed"] is not None
    ]
    citation_records = [
        record for record in case_records if record["citation"]["passed"] is not None
    ]
    safety_records = [
        record for record in case_records if record["safety"]
    ]
    latencies = [record["latency_ms"] for record in case_records]
    usage = _usage_metrics(case_records)
    return {
        "total": total,
        "passed": sum(1 for record in case_records if record["answer_passed"]),
        "failed": sum(1 for record in case_records if not record["answer_passed"]),
        "intent_accuracy": _rate(
            sum(record["intent"]["passed"] for record in intent_records),
            len(intent_records),
        ),
        "slot_accuracy": _rate(
            sum(record["slots"]["passed"] for record in slot_records),
            len(slot_records),
        ),
        "citation_accuracy": _rate(
            sum(record["citation"]["passed"] for record in citation_records),
            len(citation_records),
        ),
        "safety_pass_rate": _rate(
            sum(record["safety"].get("passed", False) for record in safety_records),
            len(safety_records),
        ),
        "latency_ms_avg": round(sum(latencies) / len(latencies), 2)
        if latencies
        else 0.0,
        "latency_ms_p50": _percentile(latencies, 0.50),
        "latency_ms_p95": _percentile(latencies, 0.95),
        "badcase_count": sum(
            1 for record in case_records if record["failure_reasons"]
        ),
        **usage,
    }
