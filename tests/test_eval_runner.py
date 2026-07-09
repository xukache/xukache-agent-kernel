from pathlib import Path

from ananhu_agent.evaluation.runner import EvalRunner
from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator


def test_eval_runner_outputs_metrics_and_badcases(tmp_path):
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","expect_contains":["一次性伤残补助金","42000"]}\n'
        '{"id":"case_2","query":"劳动能力鉴定需要准备哪些材料？","expect_contains":["这个片段不会出现，用来验证 badcase 写入"]}\n',
        encoding="utf-8",
    )
    runner = EvalRunner(create_default_orchestrator(tmp_path), tmp_path)

    metrics = runner.run(cases)

    assert metrics["total"] == 2
    assert metrics["passed"] == 1
    assert metrics["failed"] == 1
    assert (tmp_path / "metrics.json").exists()
    badcases = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "case_2" in badcases
    assert "eval_failed" in badcases
