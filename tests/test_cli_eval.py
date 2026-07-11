from typer.testing import CliRunner

from ananhu_agent.cli.main import app
from ananhu_agent.config.settings import RuntimeSettings


def _offline_cli_settings(runtime_dir, *, runtime=None):
    values = {"runtime_dir": runtime_dir}
    if runtime is not None:
        values["runtime"] = runtime
    return RuntimeSettings(_env_file=None, **values)


def test_cli_eval_outputs_metrics_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr("ananhu_agent.cli.main._cli_settings", _offline_cli_settings)
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","expect_contains":["一次性伤残补助金"]}\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["eval", str(cases)])

    assert result.exit_code == 0
    assert "Metrics:" in result.output
    assert (tmp_path / "metrics.json").exists()


def test_cli_eval_both_outputs_runtime_differential_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr("ananhu_agent.cli.main._cli_settings", _offline_cli_settings)
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","expect_contains":["一次性伤残补助金"]}\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["eval", str(cases), "--runtime", "both"])

    assert result.exit_code == 0
    assert "Runtime differential:" in result.output
    assert (tmp_path / "runtime-differential.json").exists()
