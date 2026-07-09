import os
from pathlib import Path
from typing import Annotated
from uuid import uuid4

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


@app.command("eval")
def eval_command(
    cases: Annotated[Path, typer.Argument()] = Path("data/eval/eval_cases.jsonl"),
) -> None:
    """Run local eval cases."""
    runtime_dir = Path(os.getenv("ANANHU_RUNTIME_DIR", ".ananhu-runtime"))
    orchestrator = create_default_orchestrator(runtime_dir)

    from ananhu_agent.evaluation.runner import EvalRunner

    metrics = EvalRunner(orchestrator, runtime_dir).run(cases)
    typer.echo(metrics)
    typer.echo(f"Metrics: {runtime_dir / 'metrics.json'}")


@app.command()
def chat() -> None:
    """Start an interactive consultation session."""
    runtime_dir = Path(os.getenv("ANANHU_RUNTIME_DIR", ".ananhu-runtime"))
    orchestrator = create_default_orchestrator(runtime_dir)
    session_id = _new_chat_session_id()
    turn_id = 0

    typer.echo("安安虎工伤智能助手 Agno MVP")
    typer.echo("输入 /help 查看命令，输入 /exit 退出。")

    while True:
        try:
            user_input = typer.prompt(">").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo()
            break

        if not user_input:
            continue

        normalized = user_input.lower()
        if normalized in {"/exit", "exit", "quit"}:
            break
        if normalized == "/help":
            _print_chat_help()
            continue
        if normalized == "/new":
            session_id = _new_chat_session_id()
            turn_id = 0
            typer.echo("已开始新的咨询会话。")
            continue
        if normalized in {"/context", "/trace", "/badcase"} or normalized.startswith("/feedback"):
            typer.echo("该交互能力将在后续任务补齐；当前请使用 ask/eval 输出和本地运行证据。")
            continue

        # 交互式会话由 CLI 维护轻量 session 和 turn；业务状态推进仍由编排器负责。
        turn_id += 1
        ctx = orchestrator.ask(session_id=session_id, turn_id=turn_id, user_query=user_input)
        typer.echo(ctx.final_answer)
        typer.echo(f"Trace: {runtime_dir / 'traces.jsonl'}")


def _new_chat_session_id() -> str:
    return f"cli-chat-{uuid4().hex}"


def _print_chat_help() -> None:
    typer.echo("可用命令：")
    typer.echo("/help 查看命令说明")
    typer.echo("/new 开始新的咨询会话")
    typer.echo("/context 查看当前上下文摘要（后续任务补齐）")
    typer.echo("/trace 查看最近 trace 路径（后续任务补齐）")
    typer.echo("/badcase 记录 badcase 候选（后续任务补齐）")
    typer.echo("/feedback bad 提交负向反馈（后续任务补齐）")
    typer.echo("/exit 退出会话")
