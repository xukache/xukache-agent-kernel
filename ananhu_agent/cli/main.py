import typer

from ananhu_agent import __version__

app = typer.Typer(help="安安虎工伤智能助手 CLI MVP")


@app.callback()
def main() -> None:
    """安安虎工伤智能助手 CLI MVP."""


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(f"ananhu-agent {__version__}")
