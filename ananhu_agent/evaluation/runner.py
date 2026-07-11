from __future__ import annotations

import json
import asyncio
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
from ananhu_agent.storage.jsonl_store import JsonlStore
from ananhu_agent.schemas import now_cn
from ananhu_agent.workflow.contracts import RunRequest, WorkflowRuntime


class EvalRunner:
    """本地评测执行器，负责回放 case、汇总指标并沉淀 badcase。"""

    def __init__(self, runtime: WorkflowRuntime, output_dir: Path) -> None:
        self.runtime = runtime
        self.output_dir = output_dir

    def run(self, cases_path: Path) -> dict[str, Any]:
        """运行 JSONL eval cases，返回总分与可定位失败层级的指标。"""

        rows = [
            json.loads(line)
            for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        badcases = JsonlStore(self.output_dir / "badcases.jsonl")
        passed = 0
        intent_passed = 0
        intent_total = 0
        slot_passed = 0
        slot_total = 0
        citation_passed = 0
        citation_total = 0
        capability_passed = 0
        capability_total = 0
        unsafe_total = 0
        latency_values: list[float] = []

        for index, case in enumerate(rows, start=1):
            started_at = perf_counter()
            result = asyncio.run(
                self.runtime.invoke(
                    RunRequest(
                        run_id=f"run_eval_{index}",
                        request_id=f"req_eval_{index}",
                        session_id="eval",
                        turn_id=index,
                        user_query=case["query"],
                        trusted_jurisdiction=case.get("trusted_jurisdiction", {}),
                        created_at=now_cn(),
                    )
                )
            )
            state = result.final_state
            if state is None:
                raise RuntimeError("WorkflowRuntime result missing final_state for eval")
            latency_values.append((perf_counter() - started_at) * 1000)

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

            unsafe_total += int(not score_safety(state))
            ok = score_case(result.final_answer or "", case["expect_contains"])
            if ok:
                passed += 1
                continue

            badcases.append(
                {
                    "case_id": case["id"],
                    "query": case["query"],
                    "answer": result.final_answer,
                    "issue_type": "eval_failed",
                    "expected_answer": case["expect_contains"],
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
            "unsafe_expression_rate": _rate(unsafe_total, len(rows)),
            "latency_ms_avg": round(sum(latency_values) / len(latency_values), 2)
            if latency_values
            else 0.0,
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return metrics


def _rate(passed: int, total: int) -> float | None:
    """无适用 case 时返回 None，避免把未覆盖误报成 0 分。"""

    if total == 0:
        return None
    return passed / total
