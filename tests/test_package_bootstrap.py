from typer.testing import CliRunner

from ananhu_agent import __version__
from ananhu_agent.cli.main import app


def test_package_has_version():
    assert __version__ == "0.1.0"


def test_cli_version_command():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ananhu-agent 0.1.0" in result.output
