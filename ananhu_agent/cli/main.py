import os
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer

from ananhu_agent import __version__
from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator
from ananhu_agent.schemas import AgentContext, BadcaseRecord, now_cn
from ananhu_agent.storage.runtime_stores import BadcaseStore

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
    badcase_store = BadcaseStore(runtime_dir / "badcases.jsonl")
    session_id = _new_chat_session_id()
    turn_id = 0
    latest_ctx: AgentContext | None = None

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
            latest_ctx = None
            typer.echo("已开始新的咨询会话。")
            continue
        if normalized == "/context":
            _print_context(latest_ctx)
            continue
        if normalized == "/trace":
            _print_trace(latest_ctx, runtime_dir)
            continue
        if normalized == "/badcase":
            _record_badcase(badcase_store, latest_ctx)
            continue
        if normalized.startswith("/feedback"):
            _handle_feedback(normalized, badcase_store, latest_ctx)
            continue

        # 交互式会话由 CLI 维护轻量 session 和 turn；业务状态推进仍由编排器负责。
        turn_id += 1
        latest_ctx = orchestrator.ask(session_id=session_id, turn_id=turn_id, user_query=user_input)
        typer.echo(latest_ctx.final_answer)
        typer.echo(f"Trace: {runtime_dir / 'traces.jsonl'}")


def _new_chat_session_id() -> str:
    return f"cli-chat-{uuid4().hex}"


def _print_chat_help() -> None:
    typer.echo("可用命令：")
    typer.echo("/help 查看命令说明")
    typer.echo("/new 开始新的咨询会话")
    typer.echo("/context 查看当前上下文摘要")
    typer.echo("/trace 查看最近 trace 路径")
    typer.echo("/badcase 记录 badcase 候选")
    typer.echo("/feedback bad 提交负向反馈")
    typer.echo("/exit 退出会话")


def _print_context(ctx: AgentContext | None) -> None:
    if ctx is None:
        typer.echo("暂无上下文，请先提问。")
        return
    typer.echo(f"session_id: {ctx.request.session_id}")
    typer.echo(f"turn_id: {ctx.request.turn_id}")
    typer.echo(f"active_slots: {ctx.conversation.active_slots}")


def _print_trace(ctx: AgentContext | None, runtime_dir: Path) -> None:
    if ctx is None:
        typer.echo("暂无 trace，请先提问。")
        return
    typer.echo(f"request_id: {ctx.request.request_id}")
    typer.echo(f"trace_file: {runtime_dir / 'traces.jsonl'}")


def _handle_feedback(
    command: str,
    badcase_store: BadcaseStore,
    ctx: AgentContext | None,
) -> None:
    parts = command.split()
    if len(parts) < 2:
        typer.echo("请使用 /feedback good 或 /feedback bad。")
        return
    if parts[1] == "good":
        typer.echo("已收到正向反馈。")
        return
    if parts[1] == "bad":
        _record_badcase(badcase_store, ctx)
        return
    typer.echo("请使用 /feedback good 或 /feedback bad。")


def _record_badcase(badcase_store: BadcaseStore, ctx: AgentContext | None) -> None:
    if ctx is None:
        typer.echo("暂无可记录的回答，请先提问。")
        return

    typer.echo("请选择问题类型：")
    typer.echo("1. intent_mismatch")
    typer.echo("2. calculation_error")
    typer.echo("3. missing_citation")
    typer.echo("4. region_policy_mismatch")
    issue_choice = typer.prompt("问题类型").strip()
    expected_answer = typer.prompt("期望答案或修正方向").strip()
    correction_note = typer.prompt("补充说明").strip()
    add_to_eval = typer.prompt("是否加入 eval？(y/n)").strip().lower() in {"y", "yes"}

    badcase_store.append(
        BadcaseRecord(
            id=f"badcase_{uuid4().hex[:12]}",
            request_id=ctx.request.request_id,
            session_id=ctx.request.session_id,
            turn_id=ctx.request.turn_id,
            query=ctx.request.user_query,
            predicted_intent=ctx.intent_result.intent if ctx.intent_result else None,
            issue_type=_normalize_issue_type(issue_choice),
            agent_route=ctx.agent_plan.route_agents if ctx.agent_plan else [],
            tool_calls=[result.tool_name for result in ctx.tool_results],
            actual_answer=ctx.final_answer or "",
            expected_answer=expected_answer,
            correction_note=correction_note,
            added_to_eval=add_to_eval,
            fixed=False,
            created_at=now_cn(),
        )
    )
    typer.echo(f"已记录 badcase: {ctx.request.request_id}")


def _normalize_issue_type(choice: str) -> str:
    mapping = {
        "1": "intent_mismatch",
        "2": "calculation_error",
        "3": "missing_citation",
        "4": "region_policy_mismatch",
    }
    return mapping.get(choice, choice.strip() or "other")
