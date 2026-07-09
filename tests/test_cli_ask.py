from typer.testing import CliRunner

from ananhu_agent.cli.main import app


def test_cli_ask_outputs_final_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["ask", "四川十级工伤，月工资6000，大概能赔多少钱？"],
    )

    assert result.exit_code == 0
    assert "一次性伤残补助金" in result.output
    assert "Trace:" in result.output
