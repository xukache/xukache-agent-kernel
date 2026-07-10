from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Markdown, Static, TextArea

from ananhu_agent.cli.main import _run_request
from ananhu_agent.cli.tui.modals import FeedbackModal, InformationModal
from ananhu_agent.cli.tui.presentation import (
    RunEventReducer,
    format_usage_line_from_events,
    inspector_model,
    sanitize,
    visible_result_message,
)
from ananhu_agent.cli.tui.widgets.turn import TurnWidget
from ananhu_agent.infrastructure.events.run_event_sinks import (
    CompositeRunEventSink,
    QueueRunEventSink,
    TraceRecorderRunEventSink,
)
from ananhu_agent.ports.run_event_sink import RunEventSink, RunProgressEvent
from ananhu_agent.schemas import BadcaseRecord, now_cn
from ananhu_agent.storage.runtime_stores import BadcaseStore, TraceRecorder
from ananhu_agent.workflow.contracts import RunStatus, StopReason, WorkflowResult, WorkflowRuntime


class ChatInput(TextArea):
    """输入框在本地消费 Enter，避免 TextArea 抢占后应用收不到发送动作。"""

    def on_key(self, event) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self.app.send_message()
        elif event.key in {"shift+enter", "ctrl+j"}:
            event.prevent_default()
            event.stop()
            self.insert("\n")


class AnanhuChatApp(App[None]):
    """Textual 会话入口，只编排交互，不拥有业务状态和运行时实现。"""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("ctrl+n", "new_session", "新会话"),
        Binding("ctrl+l", "clear", "清屏"),
        Binding("ctrl+r", "retry", "重试"),
        Binding("ctrl+c", "cancel", "取消"),
        Binding("f1", "help", "帮助"),
        Binding("f2", "context", "上下文"),
        Binding("f3", "trace", "Trace"),
        Binding("f4", "feedback", "反馈"),
    ]

    def __init__(
        self,
        *,
        runtime_factory: Callable[..., WorkflowRuntime],
        runtime_dir: Path,
    ) -> None:
        super().__init__()
        self.runtime_dir = runtime_dir
        self._event_queue: asyncio.Queue[RunProgressEvent] = asyncio.Queue()
        self.runtime = self._create_runtime(runtime_factory)
        self.session_id = self._new_session_id()
        self.turn_id = 0
        self.latest_result: WorkflowResult | None = None
        self.latest_request = None
        self.input_area: TextArea
        self._running_task: asyncio.Task | None = None
        self._consumer_task: asyncio.Task | None = None
        self._event_reducer = RunEventReducer()
        self._events: dict[str, list[RunProgressEvent]] = {}
        self._turns: dict[str, TurnWidget] = {}
        self._turn_widget_count = 0
        self._terminal_barriers: dict[str, asyncio.Event] = {}

    def _create_runtime(self, runtime_factory: Callable[..., WorkflowRuntime]) -> WorkflowRuntime:
        """默认组合根同时保留业务 trace 和 UI 消费的实时队列。"""

        parameters = inspect.signature(runtime_factory).parameters.values()
        accepts_event_sink = any(
            parameter.name == "event_sink" or parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters
        )
        if not accepts_event_sink:
            return runtime_factory(self.runtime_dir)
        event_sink: RunEventSink = CompositeRunEventSink(
            TraceRecorderRunEventSink(TraceRecorder(self.runtime_dir / "traces.jsonl")),
            QueueRunEventSink(self._event_queue),
        )
        return runtime_factory(self.runtime_dir, event_sink=event_sink)

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="conversation")
        yield ChatInput(id="chat-input", placeholder="输入工伤咨询问题")
        yield Static("就绪", id="chat-status")
        yield Footer()

    def on_mount(self) -> None:
        self.input_area = self.query_one("#chat-input", TextArea)
        queue = getattr(self.runtime, "events", self._event_queue)
        self._consumer_task = asyncio.create_task(self._consume_events(queue))
        self.input_area.focus()

    async def on_unmount(self) -> None:
        for task in (self._running_task, self._consumer_task):
            if task and not task.done():
                task.cancel()

    def send_message(self) -> None:
        query = self.input_area.text.strip()
        if not query or self._running_task and not self._running_task.done():
            return
        self.turn_id += 1
        request = _run_request(self.session_id, self.turn_id, query)
        self._start_request(request)
        self.input_area.clear()

    def _start_request(self, request) -> None:
        self.latest_request = request
        self._turn_widget_count += 1
        turn = TurnWidget(request.user_query, inspector_model([]), id=f"turn-{self._turn_widget_count}")
        self._turns[request.run_id] = turn
        self.query_one("#conversation", VerticalScroll).mount(turn)
        self.input_area.disabled = True
        self.query_one("#chat-status", Static).update("处理中")
        self._running_task = asyncio.create_task(self._invoke(request, turn))

    async def _invoke(self, request, turn: TurnWidget) -> None:
        try:
            result = await self.runtime.invoke(request)
            self.latest_result = result
            await turn.query_one("#assistant-message", Markdown).update(visible_result_message(result))
            turn.set_usage_line(format_usage_line_from_events(self._events.get(request.run_id, [])))
            if (
                not self._events.get(request.run_id)
                or self._terminal_barriers.get(request.run_id, asyncio.Event()).is_set()
            ):
                self._complete_turn(request.run_id, turn, result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await turn.query_one("#assistant-message", Markdown).update(f"运行失败：{sanitize(exc)}")
            turn.expand_inspector()
            turn.stop_spinner()
        finally:
            self.input_area.disabled = False
            if self._screen_stack:
                self.query_one("#chat-status", Static).update("就绪")
                self.input_area.focus()

    async def _consume_events(self, queue: asyncio.Queue) -> None:
        while True:
            event = await queue.get()
            self._apply_event(event)

    def _apply_event(self, event: RunProgressEvent) -> None:
        self._events.setdefault(event.run_id, []).append(event)
        self._event_reducer.apply(event)
        turn = self._turns.get(event.run_id)
        if turn is None:
            return
        turn.update_inspector(inspector_model(self._events[event.run_id]))
        state = self._event_reducer.state_for(event.run_id)
        # 终止屏障是运行时清理协议，必须独立于本地展示错误被消费。
        if state.terminal_barrier_seen:
            self._terminal_barriers.setdefault(event.run_id, asyncio.Event()).set()
        if state.error_code:
            turn.expand_inspector()
            turn.stop_spinner()
            self.query_one("#chat-status", Static).update("事件流异常")
        elif state.terminal_barrier_seen:
            self._complete_turn(event.run_id, turn, self.latest_result)

    def _complete_turn(self, run_id: str, turn: TurnWidget, result: WorkflowResult | None) -> None:
        turn.stop_spinner()
        turn.set_usage_line(format_usage_line_from_events(self._events.get(run_id, [])))
        failed = result is not None and result.status == RunStatus.FAILED
        if failed:
            turn.expand_inspector()
        else:
            turn.collapse_inspector()

    def action_new_session(self) -> None:
        if self._running_task and not self._running_task.done():
            return
        self.session_id = self._new_session_id()
        self.turn_id = 0
        self.latest_result = None
        self.latest_request = None
        self.action_clear()

    def action_clear(self) -> None:
        self.query_one("#conversation", VerticalScroll).remove_children()

    def action_retry(self) -> None:
        if self.latest_request is None or self._running_task and not self._running_task.done():
            return
        previous = self.latest_request
        request = previous.model_copy(update={"run_id": f"run_{uuid4().hex[:12]}"})
        self._start_request(request)

    async def action_cancel(self) -> None:
        if self._running_task and not self._running_task.done():
            run_id = self.latest_request.run_id if self.latest_request else ""
            worker = self._running_task
            terminal_barrier = self._terminal_barriers.setdefault(run_id, asyncio.Event())
            worker.cancel()
            try:
                if not terminal_barrier.is_set():
                    await asyncio.wait_for(terminal_barrier.wait(), timeout=2)
            except TimeoutError:
                # 超时属于本地退出异常，不能伪造运行时业务事件。
                self.query_one("#chat-status", Static).update("本地退出异常")
            try:
                await worker
            except asyncio.CancelledError:
                pass
        # Ctrl+C 同时承担空闲会话退出职责；运行中的路径已在此之前完成屏障等待与 worker 回收。
        self.exit(return_code=0)

    def action_help(self) -> None:
        self.push_screen(InformationModal("帮助", "Enter 发送；Shift+Enter 或 Ctrl+J 换行。"))

    def action_context(self) -> None:
        if self.latest_result is None:
            content = "暂无上下文"
        else:
            state = self.latest_result.final_state
            content = json.dumps({
                "session_id": self.latest_result.session_id,
                "phase": state.phase.value if state else None,
                "case_facts": state.case_facts if state else {},
            }, ensure_ascii=False, indent=2)
        self.push_screen(InformationModal("上下文", content))

    def action_trace(self) -> None:
        content = "暂无 trace" if self.latest_result is None else json.dumps({
            "request_id": self.latest_result.request_id,
            "trace_file": str(self.runtime_dir / "traces.jsonl"),
        }, ensure_ascii=False, indent=2)
        self.push_screen(InformationModal("Trace", content))

    def action_feedback(self) -> None:
        self.push_screen(FeedbackModal(), self._handle_feedback)

    def _handle_feedback(self, feedback: dict[str, str | bool] | None) -> None:
        if feedback is None:
            return
        if feedback["kind"] == "good":
            self.query_one("#chat-status", Static).update("已收到正向反馈")
            return
        result = self.latest_result
        request = self.latest_request
        if result is None or request is None:
            self.query_one("#chat-status", Static).update("暂无可记录的回答，请先提问")
            return
        state = result.final_state
        BadcaseStore(self.runtime_dir / "badcases.jsonl").append(BadcaseRecord(
            id=f"badcase_{uuid4().hex[:12]}",
            request_id=request.request_id,
            session_id=request.session_id,
            turn_id=request.turn_id,
            query=request.user_query,
            predicted_intent=(state.intent_result or {}).get("intent") if state else None,
            issue_type=self._normalize_issue_type(feedback.get("issue_type", "")),
            agent_route=(state.execution_plan or {}).get("route_agents", []) if state else [],
            tool_calls=[item.get("tool_name", "") for item in (state.capability_results if state else []) if item.get("tool_name")],
            actual_answer=result.final_answer or result.clarification_question or "",
            expected_answer=feedback.get("expected_answer", ""),
            correction_note=feedback.get("correction_note", ""),
            added_to_eval=bool(feedback.get("added_to_eval", False)),
            fixed=False,
            created_at=now_cn(),
        ))
        self.query_one("#chat-status", Static).update(f"已记录 badcase: {request.request_id}")

    @staticmethod
    def _normalize_issue_type(choice: str) -> str:
        return {
            "1": "intent_mismatch",
            "2": "calculation_error",
            "3": "missing_citation",
            "4": "region_policy_mismatch",
        }.get(choice.strip(), choice.strip() or "other")

    @staticmethod
    def _new_session_id() -> str:
        return f"cli-chat-{uuid4().hex}"
