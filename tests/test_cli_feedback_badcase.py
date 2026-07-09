from typer.testing import CliRunner

from ananhu_agent.cli.main import app


def test_cli_chat_feedback_bad_writes_badcase(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["chat"],
        input=(
            "四川十级工伤，月工资6000，大概能赔多少钱？\n"
            "/feedback bad\n"
            "4\n"
            "应该核对地方政策\n"
            "地区政策不匹配\n"
            "n\n"
            "/exit\n"
        ),
    )

    assert result.exit_code == 0
    badcases = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "region_policy_mismatch" in badcases
    assert "应该核对地方政策" in badcases


def test_cli_chat_trace_prints_latest_request_id(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["chat"],
        input="四川十级工伤，月工资6000，大概能赔多少钱？\n/trace\n/exit\n",
    )

    assert result.exit_code == 0
    assert "request_id:" in result.output
