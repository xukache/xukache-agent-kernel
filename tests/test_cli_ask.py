from typer.testing import CliRunner

from ananhu_agent.cli.main import app
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.workflow.contracts import RunStatus, WorkflowResult


def _offline_cli_settings(runtime_dir, *, runtime=None):
    values = {"runtime_dir": runtime_dir}
    if runtime is not None:
        values["runtime"] = runtime
    return RuntimeSettings(_env_file=None, **values)


def test_cli_ask_outputs_final_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr("ananhu_agent.cli.main._cli_settings", _offline_cli_settings)
    result = CliRunner().invoke(
        app,
        [
            "ask",
            "四川十级工伤，月工资6000，大概能赔多少钱？",
            "--province",
            "四川省",
        ],
    )

    assert result.exit_code == 0
    assert "一次性伤残补助金" in result.output
    assert "Trace:" in result.output


def test_cli_ask_never_prints_blank_result(tmp_path, monkeypatch):
    class EmptyRuntime:
        async def invoke(self, request):
            return WorkflowResult(
                run_id=request.run_id,
                request_id=request.request_id,
                session_id=request.session_id,
                status=RunStatus.FAILED,
                stop_reason=None,
            )

    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr("ananhu_agent.cli.main._cli_settings", _offline_cli_settings)
    monkeypatch.setattr(
        "ananhu_agent.cli.main.create_default_runtime",
        lambda _, __: EmptyRuntime(),
    )

    result = CliRunner().invoke(app, ["ask", "测试空结果"])

    assert result.exit_code == 0
    assert "系统暂时无法生成有效回复" in result.output
