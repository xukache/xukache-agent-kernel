from pathlib import Path
import json

from ananhu_agent.evaluation.runner import EvalRunner
from ananhu_agent.ports.model_gateway import ModelErrorCode, ModelGatewayError
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.workflow.contracts import WorkflowRuntime


def test_eval_runner_outputs_metrics_and_badcases(tmp_path):
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","trusted_jurisdiction":{"province":"四川省"},"expect_contains":["一次性伤残补助金","42000"]}\n'
        '{"id":"case_2","query":"劳动能力鉴定需要准备哪些材料？","trusted_jurisdiction":{"province":"四川省"},"expect_contains":["这个片段不会出现，用来验证 badcase 写入"]}\n',
        encoding="utf-8",
    )
    runner = EvalRunner(create_default_runtime(tmp_path), tmp_path)

    metrics = runner.run(cases)

    assert metrics["total"] == 2
    assert metrics["passed"] == 1
    assert metrics["failed"] == 1
    assert (tmp_path / "metrics.json").exists()
    badcases = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "case_2" in badcases
    assert "eval_failed" in badcases


def test_eval_runner_outputs_layered_metrics(tmp_path):
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","trusted_jurisdiction":{"province":"四川省"},"expected_intent":"payment_calculation","expected_slots":{"province":"四川省","disability_grade":"十级"},"expect_contains":["一次性伤残补助金"],"expected_citations":["四川省工伤保险条例实施办法"]}\n',
        encoding="utf-8",
    )
    runner = EvalRunner(create_default_runtime(tmp_path), tmp_path)

    metrics = runner.run(cases)

    assert metrics["intent_accuracy"] == 1.0
    assert metrics["slot_accuracy"] == 1.0
    assert metrics["citation_accuracy"] == 1.0
    assert metrics["capability_success_rate"] == 1.0
    assert "latency_ms_avg" in metrics


def test_eval_runner_writes_case_level_evidence_artifact(tmp_path):
    cases = tmp_path / "real_smoke_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","evaluation_kind":"real_smoke","category":"payment_calculation",'
        '"expert_scenario":"验证待遇测算和政策引用","risk_focus":"金额只能作为辅助测算",'
        '"query":"四川十级工伤，月工资6000，大概能赔多少钱？",'
        '"trusted_jurisdiction":{"province":"四川省"},'
        '"expected_intent":"payment_calculation",'
        '"expected_slots":{"province":"四川省","disability_grade":"十级","monthly_wage":6000},'
        '"expected_citations":["四川省工伤保险条例实施办法"],'
        '"expect_contains":["一次性伤残补助金","42000","风险提示"]}\n',
        encoding="utf-8",
    )

    metrics = EvalRunner(create_default_runtime(tmp_path), tmp_path).run(cases)

    artifact = json.loads((tmp_path / "evaluation.json").read_text(encoding="utf-8"))
    record = artifact["cases"][0]
    assert artifact["schema_version"] == "evaluation.v1"
    assert artifact["evaluation_kind"] == "real_smoke"
    assert metrics["safety_pass_rate"] == 1.0
    assert record["model_calls"][0]["provider"] == "fake"
    assert record["model_calls"][0]["usage"]["usage_source"] == "fake"
    assert record["retrieval"]["evidence_count"] > 0
    assert record["citation"]["passed"] is True
    assert record["safety"]["passed"] is True
    assert record["latency_ms"] >= 0


def test_eval_runner_classifies_failed_case_in_badcase_record(tmp_path):
    cases = tmp_path / "real_smoke_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","evaluation_kind":"real_smoke","category":"labor_capacity",'
        '"expert_scenario":"验证回答失败分类","risk_focus":"失败必须可定位",'
        '"query":"劳动能力鉴定需要准备哪些材料？",'
        '"trusted_jurisdiction":{"province":"四川省"},'
        '"expected_intent":"labor_capacity",'
        '"expect_contains":["不存在的验收片段"]}\n',
        encoding="utf-8",
    )

    EvalRunner(create_default_runtime(tmp_path), tmp_path).run(cases)

    badcases = [
        json.loads(line)
        for line in (tmp_path / "badcases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    eval_badcase = next(row for row in badcases if row["issue_type"] == "eval_failed")
    assert "response_inconsistency" in eval_badcase["failure_reasons"]


def test_eval_runner_converts_provider_failure_into_report_and_badcase(tmp_path):
    class FailingRuntime(WorkflowRuntime):
        async def invoke(self, request):
            raise ModelGatewayError(
                ModelErrorCode.TIMEOUT,
                "provider timeout",
                provider="openai_compatible",
                retryable=True,
            )

    cases = tmp_path / "real_smoke_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","evaluation_kind":"real_smoke","category":"payment_calculation",'
        '"expert_scenario":"验证 provider 失败收敛","risk_focus":"失败必须写入报告",'
        '"query":"四川十级工伤，月工资6000，大概能赔多少钱？",'
        '"trusted_jurisdiction":{"province":"四川省"},'
        '"expected_intent":"payment_calculation",'
        '"expect_contains":["一次性伤残补助金"]}\n',
        encoding="utf-8",
    )

    EvalRunner(FailingRuntime(), tmp_path).run(cases)

    artifact = json.loads((tmp_path / "evaluation.json").read_text(encoding="utf-8"))
    record = artifact["cases"][0]
    assert record["status"] == "failed"
    assert "runtime_or_recovery_error" in record["failure_reasons"]
    assert "timeout_error" in record["failure_reasons"]
    badcases = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "runtime_or_recovery_error" in badcases
