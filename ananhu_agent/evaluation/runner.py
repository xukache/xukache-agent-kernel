from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ananhu_agent.evaluation.metrics import score_case
from ananhu_agent.orchestrator.orchestrator import AgentOrchestrator
from ananhu_agent.storage.jsonl_store import JsonlStore


class EvalRunner:
    """本地评测执行器，负责回放 case、汇总指标并沉淀 badcase。"""

    def __init__(self, orchestrator: AgentOrchestrator, output_dir: Path) -> None:
        self.orchestrator = orchestrator
        self.output_dir = output_dir

    def run(self, cases_path: Path) -> dict[str, Any]:
        """运行 JSONL eval cases，返回 total/passed/failed 指标。"""

        rows = [
            json.loads(line)
            for line in cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        badcases = JsonlStore(self.output_dir / "badcases.jsonl")
        passed = 0

        for index, case in enumerate(rows, start=1):
            ctx = self.orchestrator.ask("eval", index, case["query"])
            ok = score_case(ctx.final_answer or "", case["expect_contains"])
            if ok:
                passed += 1
                continue

            badcases.append(
                {
                    "case_id": case["id"],
                    "query": case["query"],
                    "answer": ctx.final_answer,
                    "issue_type": "eval_failed",
                    "expected_answer": case["expect_contains"],
                }
            )

        metrics = {"total": len(rows), "passed": passed, "failed": len(rows) - passed}
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return metrics
