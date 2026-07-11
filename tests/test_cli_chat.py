from typer.testing import CliRunner

from ananhu_agent.cli.main import app
from ananhu_agent.config.settings import RuntimeSettings


def _offline_cli_settings(runtime_dir, *, runtime=None):
    values = {"runtime_dir": runtime_dir}
    if runtime is not None:
        values["runtime"] = runtime
    return RuntimeSettings(_env_file=None, **values)


def test_cli_chat_requires_interactive_ansi_terminal(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["chat"],
        input="",
    )

    assert result.exit_code == 2
    assert result.stderr == "ananhu-agent chat requires an interactive ANSI terminal\n"


def test_noninteractive_commands_execute_without_importing_textual_chat_app(tmp_path, monkeypatch):
    import sys

    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr("ananhu_agent.cli.main._cli_settings", _offline_cli_settings)
    sys.modules.pop("ananhu_agent.cli.tui.app", None)
    assert CliRunner().invoke(app, ["version"]).exit_code == 0
    assert CliRunner().invoke(app, ["ask", "四川十级工伤，月工资6000"] ).exit_code == 0
    cases = tmp_path / "cases.jsonl"
    cases.write_text('{"id":"case_1","query":"四川十级工伤，月工资6000","expect_contains":["一次性伤残补助金"]}\n', encoding="utf-8")
    assert CliRunner().invoke(app, ["eval", str(cases)]).exit_code == 0

    assert "ananhu_agent.cli.tui.app" not in sys.modules
