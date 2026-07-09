import json

from typer.testing import CliRunner

from ananhu_agent.cli.main import app


def test_cli_chat_runs_until_exit(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["chat"],
        input="四川十级工伤，月工资6000，大概能赔多少钱？\n/exit\n",
    )

    assert result.exit_code == 0
    assert "安安虎工伤智能助手 Agno MVP" in result.output
    assert "一次性伤残补助金" in result.output
    assert "Trace:" in result.output


def test_cli_chat_help_command(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(app, ["chat"], input="/help\n/exit\n")

    assert result.exit_code == 0
    assert "/new" in result.output
    assert "/context" in result.output
    assert "/trace" in result.output
    assert "/feedback bad" in result.output


def test_cli_chat_reuses_session_and_increments_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["chat"],
        input=(
            "四川十级工伤，月工资6000，大概能赔多少钱？\n"
            "劳动能力鉴定需要准备哪些材料？\n"
            "/exit\n"
        ),
    )

    assert result.exit_code == 0
    states = [
        json.loads(line)
        for line in (tmp_path / "task_states.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [state["turn_id"] for state in states] == [1, 2]
    assert len({state["session_id"] for state in states}) == 1
