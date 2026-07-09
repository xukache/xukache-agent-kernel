import os
from pathlib import Path

import typer

from ananhu_agent import __version__
from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator

app = typer.Typer(help="安安虎工伤智能助手 CLI MVP")


@app.callback()
def main() -> None:
    """安安虎工伤智能助手 CLI MVP."""


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(f"ananhu-agent {__version__}")


@app.command()
def ask(query: str) -> None:
    """Ask one work injury consultation question."""
    runtime_dir = Path(os.getenv("ANANHU_RUNTIME_DIR", ".ananhu-runtime"))
    orchestrator = create_default_orchestrator(runtime_dir)
    ctx = orchestrator.ask(session_id="cli", turn_id=1, user_query=query)
    typer.echo(ctx.final_answer)
    typer.echo(f"Trace: {runtime_dir / 'traces.jsonl'}")
