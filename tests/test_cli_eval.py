from typer.testing import CliRunner

from ananhu_agent.cli.main import app


def test_cli_eval_outputs_metrics_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","expect_contains":["一次性伤残补助金"]}\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["eval", str(cases)])

    assert result.exit_code == 0
    assert "Metrics:" in result.output
    assert (tmp_path / "metrics.json").exists()
