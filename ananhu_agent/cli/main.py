import os
import asyncio
import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer

from ananhu_agent import __version__
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.cli.tui.presentation import visible_result_message
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.schemas import BadcaseRecord, now_cn
from ananhu_agent.storage.runtime_stores import BadcaseStore, TraceRecorder
from ananhu_agent.workflow.contracts import RunRequest, WorkflowResult, WorkflowRuntime, WorkflowState

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
    runtime: WorkflowRuntime = create_default_runtime(runtime_dir)
    result = asyncio.run(runtime.invoke(_run_request("cli", 1, query)))
    typer.echo(visible_result_message(result))
    typer.echo(f"Trace: {runtime_dir / 'traces.jsonl'}")


@app.command("eval")
def eval_command(
    cases: Annotated[Path, typer.Argument()] = Path("data/eval/eval_cases.jsonl"),
    runtime: Annotated[str | None, typer.Option(help="运行时：native、langgraph 或 both")] = None,
) -> None:
    """Run local eval cases."""
    runtime_dir = Path(os.getenv("ANANHU_RUNTIME_DIR", ".ananhu-runtime"))
    if runtime == "both":
        _run_differential_eval(cases, runtime_dir)
        return
    if runtime not in {None, "native", "langgraph"}:
        raise typer.BadParameter("runtime 必须是 native、langgraph 或 both")
    selected_runtime: WorkflowRuntime = create_default_runtime(
        runtime_dir,
        RuntimeSettings(runtime_dir=runtime_dir, runtime=runtime) if runtime else None,
    )

    from ananhu_agent.evaluation.runner import EvalRunner

    metrics = EvalRunner(selected_runtime, runtime_dir).run(cases)
    typer.echo(metrics)
    typer.echo(f"Metrics: {runtime_dir / 'metrics.json'}")


def _run_differential_eval(cases: Path, runtime_dir: Path) -> None:
    """对同一 eval 数据运行 Native/LangGraph 并写入差分产物。"""

    from ananhu_agent.evaluation.differential import RuntimeDifferentialRunner

    native_dir = runtime_dir / "native"
    langgraph_dir = runtime_dir / "langgraph"
    rows = [
        json.loads(line)
        for line in cases.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    runner = RuntimeDifferentialRunner(
        native_runtime=create_default_runtime(
            native_dir,
            RuntimeSettings(runtime_dir=native_dir, runtime="native"),
        ),
        langgraph_runtime=create_default_runtime(
            langgraph_dir,
            RuntimeSettings(runtime_dir=langgraph_dir, runtime="langgraph"),
        ),
        native_trace=TraceRecorder(native_dir / "traces.jsonl"),
        langgraph_trace=TraceRecorder(langgraph_dir / "traces.jsonl"),
        artifact_path=runtime_dir / "runtime-differential.json",
    )
    report = runner.run_cases(rows)
    typer.echo(
        {
            "schema_version": report.schema_version,
            "total": report.total,
            "equivalent": report.equivalent,
            "different": report.different,
        }
    )
    typer.echo(f"Runtime differential: {runtime_dir / 'runtime-differential.json'}")
    if report.different:
        raise typer.Exit(code=1)


@app.command()
def chat() -> None:
    """Start an interactive consultation session."""
    runtime_dir = Path(os.getenv("ANANHU_RUNTIME_DIR", ".ananhu-runtime"))
    runtime = create_default_runtime(runtime_dir)
    badcase_store = BadcaseStore(runtime_dir / "badcases.jsonl")
    session_id = _new_chat_session_id()
    turn_id = 0
    latest_result: WorkflowResult | None = None

    typer.echo("安安虎工伤智能助手 CLI")
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
            latest_result = None
            typer.echo("已开始新的咨询会话。")
            continue
        if normalized == "/context":
            _print_context(_latest_state(latest_result))
            continue
        if normalized == "/trace":
            _print_trace(latest_result, runtime_dir)
            continue
        if normalized == "/badcase":
            _record_badcase(badcase_store, latest_result)
            continue
        if normalized.startswith("/feedback"):
            _handle_feedback(normalized, badcase_store, latest_result)
            continue

        # 交互式会话由 CLI 维护轻量 session 和 turn；业务状态推进由 WorkflowRuntime 负责。
        turn_id += 1
        latest_result = asyncio.run(runtime.invoke(_run_request(session_id, turn_id, user_input)))
        typer.echo(visible_result_message(latest_result))
        typer.echo(f"Trace: {runtime_dir / 'traces.jsonl'}")


def _new_chat_session_id() -> str:
    return f"cli-chat-{uuid4().hex}"


def _run_request(session_id: str, turn_id: int, query: str) -> RunRequest:
    return RunRequest(
        run_id=f"run_{uuid4().hex[:12]}",
        request_id=f"req_{uuid4().hex[:12]}",
        session_id=session_id,
        turn_id=turn_id,
        user_query=query,
        created_at=now_cn(),
    )


def _print_chat_help() -> None:
    typer.echo("可用命令：")
    typer.echo("/help 查看命令说明")
    typer.echo("/new 开始新的咨询会话")
    typer.echo("/context 查看当前上下文摘要")
    typer.echo("/trace 查看最近 trace 路径")
    typer.echo("/badcase 记录 badcase 候选")
    typer.echo("/feedback bad 提交负向反馈")
    typer.echo("/exit 退出会话")


def _latest_state(result: WorkflowResult | None) -> WorkflowState | None:
    return result.final_state if result else None


def _print_context(state: WorkflowState | None) -> None:
    if state is None:
        typer.echo("暂无上下文，请先提问。")
        return
    typer.echo(f"session_id: {state.session_id}")
    typer.echo(f"phase: {state.phase.value}")
    typer.echo(f"case_facts: {state.case_facts}")


def _print_trace(result: WorkflowResult | None, runtime_dir: Path) -> None:
    if result is None:
        typer.echo("暂无 trace，请先提问。")
        return
    typer.echo(f"request_id: {result.request_id}")
    typer.echo(f"trace_file: {runtime_dir / 'traces.jsonl'}")


def _handle_feedback(
    command: str,
    badcase_store: BadcaseStore,
    result: WorkflowResult | None,
) -> None:
    parts = command.split()
    if len(parts) < 2:
        typer.echo("请使用 /feedback good 或 /feedback bad。")
        return
    if parts[1] == "good":
        typer.echo("已收到正向反馈。")
        return
    if parts[1] == "bad":
        _record_badcase(badcase_store, result)
        return
    typer.echo("请使用 /feedback good 或 /feedback bad。")


def _record_badcase(badcase_store: BadcaseStore, result: WorkflowResult | None) -> None:
    state = _latest_state(result)
    if result is None or state is None:
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
            request_id=state.request_id,
            session_id=state.session_id,
            turn_id=state.case_facts.get("turn_id", 0),
            query=state.case_facts.get("user_query", ""),
            predicted_intent=state.intent_result.get("intent") if state.intent_result else None,
            issue_type=_normalize_issue_type(issue_choice),
            agent_route=state.execution_plan.get("route_agents", []) if state.execution_plan else [],
            tool_calls=[
                capability.get("tool_name", "")
                for capability in state.capability_results
                if capability.get("tool_name")
            ],
            actual_answer=result.final_answer or result.clarification_question or "",
            expected_answer=expected_answer,
            correction_note=correction_note,
            added_to_eval=add_to_eval,
            fixed=False,
            created_at=now_cn(),
        )
    )
    typer.echo(f"已记录 badcase: {state.request_id}")


def _normalize_issue_type(choice: str) -> str:
    mapping = {
        "1": "intent_mismatch",
        "2": "calculation_error",
        "3": "missing_citation",
        "4": "region_policy_mismatch",
    }
    return mapping.get(choice, choice.strip() or "other")
