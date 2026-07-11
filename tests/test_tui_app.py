import asyncio
import json
import secrets

import pytest
from textual.widgets import Checkbox, Input, Static

from ananhu_agent.ports.run_event_sink import (
    ModelFinishedEvent,
    ModelFinishedPayload,
    NodeStartedEvent,
    RunFinishedEvent,
)
from ananhu_agent.workflow.contracts import (
    RunStatus,
    StopReason,
    WorkflowPhase,
    WorkflowResult,
    WorkflowState,
)


class BarrierRuntime:
    """用于 Pilot 的运行时，显式控制进度事件和终止屏障。"""

    def __init__(self, *, failed: bool = False, report_usage: bool = False) -> None:
        self.events: asyncio.Queue = asyncio.Queue()
        self.requests = []
        self.release = asyncio.Event()
        self.failed = failed
        self.report_usage = report_usage

    async def invoke(self, request):
        self.requests.append(request)
        await self.events.put(NodeStartedEvent(
            run_id=request.run_id,
            request_id=request.request_id,
            session_id=request.session_id,
            node_id="understand",
            sequence_no=1,
            public_payload={"phase": "understand"},
        ))
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            await self.events.put(RunFinishedEvent(
                run_id=request.run_id,
                request_id=request.request_id,
                session_id=request.session_id,
                sequence_no=2,
                public_payload={"status": "cancelled", "stop_reason": "user_cancelled"},
            ))
            raise
        status = RunStatus.FAILED if self.failed else RunStatus.COMPLETED
        stop_reason = StopReason.CAPABILITY_FAILED if self.failed else StopReason.COMPLETE
        if self.report_usage:
            await self.events.put(ModelFinishedEvent(
                run_id=request.run_id,
                request_id=request.request_id,
                session_id=request.session_id,
                logical_call_id="model_1",
                sequence_no=2,
                public_payload=ModelFinishedPayload(
                    profile="intent_fast",
                    provider="provider",
                    model="model",
                    usage={
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "total_tokens": 120,
                        "usage_source": "provider",
                        "reported": True,
                    },
                    latency_ms=1_000,
                ),
            ))
        await self.events.put(RunFinishedEvent(
            run_id=request.run_id,
            request_id=request.request_id,
            session_id=request.session_id,
            sequence_no=3 if self.report_usage else 2,
            public_payload={"status": status.value, "stop_reason": stop_reason.value},
        ))
        state = WorkflowState(
            run_id=request.run_id,
            request_id=request.request_id,
            session_id=request.session_id,
            turn_id=request.turn_id,
            phase=WorkflowPhase.COMPLETE,
            status=status,
            stop_reason=stop_reason,
        )
        return WorkflowResult(
            run_id=request.run_id,
            request_id=request.request_id,
            session_id=request.session_id,
            status=status,
            final_state=state,
            final_answer="完成",
            stop_reason=stop_reason,
        )


@pytest.mark.asyncio
async def test_chat_updates_events_live_and_collapses_after_terminal_barrier(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        turn = app.query_one("#turn-1")
        assert turn.query_one("#run-inspector").running_node == "understand"
        assert turn.inspector_collapsed is False
        runtime.release.set()
        await pilot.pause()
        await pilot.pause()
        assert turn.inspector_collapsed is True


@pytest.mark.asyncio
async def test_double_enter_only_invokes_runtime_once(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter", "enter")
        await pilot.pause()
        assert len(runtime.requests) == 1
        runtime.release.set()


@pytest.mark.asyncio
async def test_retry_keeps_request_id_and_changes_run_id(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        first = runtime.requests[0]
        runtime.release.set()
        await pilot.pause()
        await pilot.press("ctrl+r")
        await pilot.pause()
        second = runtime.requests[1]
        assert second.request_id == first.request_id
        assert second.run_id != first.run_id
        runtime.release.set()


@pytest.mark.asyncio
async def test_ctrl_j_inserts_newline_without_sending(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "ctrl+j")
        assert app.input_area.text == "hi\n"
        assert runtime.requests == []


@pytest.mark.asyncio
async def test_shift_enter_inserts_newline_without_sending(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "shift+enter")
        assert app.input_area.text == "hi\n"
        assert runtime.requests == []


@pytest.mark.asyncio
async def test_cancel_waits_for_terminal_barrier_and_reaps_worker(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        task = app._running_task
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert task is not None and task.done()
        assert app.input_area.disabled is False


@pytest.mark.asyncio
async def test_ctrl_c_cancels_run_then_exits_textual_app(tmp_path):
    """取消完成后必须退出，真实 PTY 才能以 0 正常回收进程。"""

    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        await pilot.press("ctrl+c")
        await pilot.pause()

        assert app._running_task is not None and app._running_task.done()
        assert app._exit is True
        assert app.return_code == 0


@pytest.mark.asyncio
async def test_ctrl_c_exits_textual_app_while_idle(tmp_path):
    """空闲 TUI 也应把 Ctrl+C 解释为正常退出。"""

    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("ctrl+c")
        await pilot.pause()

        assert app._exit is True
        assert app.return_code == 0


@pytest.mark.asyncio
async def test_ctrl_c_exits_textual_app_after_completed_turn(tmp_path):
    """已完成咨询后 Ctrl+C 不应变成无动作。"""

    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        runtime.release.set()
        await pilot.pause()
        await pilot.pause()

        await pilot.press("ctrl+c")
        await pilot.pause()

        assert app._exit is True
        assert app.return_code == 0


@pytest.mark.asyncio
async def test_completed_turn_renders_aggregate_model_usage(tmp_path):
    """本轮完成后 usage 需从已有模型结果协议生成可见状态行。"""

    from ananhu_agent.cli.tui.app import AnanhuChatApp
    runtime = BarrierRuntime(report_usage=True)
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        runtime.release.set()
        await pilot.pause()
        await pilot.pause()

        assert "Σ 120 tokens" in str(app.query_one("#turn-1 .turn-usage").render())


@pytest.mark.asyncio
async def test_runtime_exception_is_sanitized_before_rendering(tmp_path):
    """异常文本属于瞬态展示数据，不能绕过既有脱敏边界。"""

    from ananhu_agent.cli.tui.app import AnanhuChatApp

    canary = secrets.token_urlsafe(24)

    class FailingRuntime(BarrierRuntime):
        async def invoke(self, request):
            await asyncio.sleep(0)
            raise RuntimeError(f"provider failed with token={canary}")

    app = AnanhuChatApp(runtime_factory=lambda _: FailingRuntime(), runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()

        assert app._running_task is not None and app._running_task.done()
        rendered = app.query_one("#assistant-message")._markdown
        assert canary not in rendered
        assert "token=***" in rendered


@pytest.mark.asyncio
async def test_manual_expansion_survives_normal_completion(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        turn = app.query_one("#turn-1")
        runtime.release.set()
        await pilot.pause()
        await pilot.pause()
        assert turn.inspector_collapsed is True
        await pilot.click("#inspector-toggle")
        assert turn.inspector_collapsed is False


@pytest.mark.asyncio
async def test_failed_path_forces_expansion_over_manual_collapse(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime(failed=True)
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        turn = app.query_one("#turn-1")
        turn.collapse_inspector(force=True)
        runtime.release.set()
        await pilot.pause()
        await pilot.pause()
        assert turn.inspector_collapsed is False


@pytest.mark.asyncio
async def test_sequence_gap_stops_spinner_and_keeps_local_failure(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        request = runtime.requests[0]
        turn = app.query_one("#turn-1")
        await runtime.events.put(NodeStartedEvent(
            run_id=request.run_id, request_id=request.request_id, session_id=request.session_id,
            node_id="plan", sequence_no=3, public_payload={"phase": "plan"},
        ))
        await pilot.pause()
        assert app._event_reducer.state_for(request.run_id).error_code == "event_sequence_gap"
        assert str(app.query_one("#chat-status").render()) == "事件流异常"
        assert turn.query_one("#run-spinner").display is False
        assert turn.query_one("#run-spinner").running is False
        runtime.release.set()


@pytest.mark.asyncio
async def test_cancel_after_sequence_gap_consumes_terminal_barrier_without_timeout(tmp_path):
    """本地 gap 不应阻断运行时终止屏障，取消必须立即回收 worker。"""

    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        request = runtime.requests[0]
        turn = app.query_one("#turn-1")
        await runtime.events.put(NodeStartedEvent(
            run_id=request.run_id, request_id=request.request_id, session_id=request.session_id,
            node_id="plan", sequence_no=3, public_payload={"phase": "plan"},
        ))
        await pilot.pause()

        started_at = asyncio.get_running_loop().time()
        await app.action_cancel()
        elapsed = asyncio.get_running_loop().time() - started_at

        state = app._event_reducer.state_for(request.run_id)
        assert elapsed < 0.5
        assert app._terminal_barriers[request.run_id].is_set()
        assert app._running_task is not None and app._running_task.done()
        assert state.error_code == "event_sequence_gap"
        assert turn.query_one("#run-spinner").running is False


@pytest.mark.asyncio
async def test_session_reuse_new_session_and_clear_preserve_persisted_runtime_state(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp
    from ananhu_agent.runtime import create_default_runtime

    app = AnanhuChatApp(runtime_factory=create_default_runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("o", "n", "e", "enter")
        await app._running_task
        await pilot.pause()
        await pilot.press("t", "w", "o", "enter")
        await app._running_task
        await pilot.pause()
        first_session = app.latest_request.session_id
        states = [
            json.loads(line)
            for line in (tmp_path / "task_states.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        assert [state["turn_id"] for state in states] == [1, 2]
        assert {state["session_id"] for state in states} == {first_session}

        persisted_before_clear = {
            filename: (tmp_path / filename).read_text(encoding="utf-8")
            for filename in ("task_states.jsonl", "session_states.jsonl", "traces.jsonl")
        }
        await pilot.press("ctrl+l")
        assert app.turn_id == 2
        assert app.session_id == first_session
        assert len(app.query(".turn-user")) == 0
        assert persisted_before_clear == {
            filename: (tmp_path / filename).read_text(encoding="utf-8")
            for filename in persisted_before_clear
        }

        await pilot.press("ctrl+n")
        assert app.turn_id == 0
        assert app.session_id != first_session


@pytest.mark.asyncio
async def test_help_context_trace_and_feedback_modals_open_and_close(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        runtime.release.set()
        await pilot.pause()
        await pilot.pause()
        for key, expected in (("f1", "Enter"), ("f2", "case_facts"), ("f3", "traces.jsonl"), ("f4", "反馈")):
            await pilot.press(key)
            await pilot.pause()
            assert app.screen.__class__.__name__.endswith("Modal")
            content = (
                app.screen.query_one(".modal-title").render()
                if key == "f4"
                else app.screen.query_one("#modal-information").render()
            )
            assert expected in str(content)
            if key == "f2":
                assert app.latest_result.session_id in str(app.screen.query_one("#modal-information").render())
                assert "complete" in str(app.screen.query_one("#modal-information").render())
            if key == "f3":
                assert app.latest_result.request_id in str(app.screen.query_one("#modal-information").render())
            await pilot.press("escape")
            await pilot.pause()
            assert not app.screen.__class__.__name__.endswith("Modal")


@pytest.mark.asyncio
async def test_bad_feedback_can_add_record_to_eval_jsonl(tmp_path):
    """负向反馈保留旧 CLI 的加入 eval 选择，并写入既有 JSONL 协议。"""

    from ananhu_agent.cli.tui.app import AnanhuChatApp
    from ananhu_agent.storage.runtime_stores import BadcaseStore

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        runtime.release.set()
        await pilot.pause()
        await pilot.pause()
        await pilot.press("f4")
        await pilot.click("#feedback-bad")
        await pilot.click("#added-to-eval")
        assert app.screen.query_one("#added-to-eval", Checkbox).value is True
        app.screen.query_one("#issue-type", Input).value = "4"
        await pilot.click("#feedback-submit")
        await pilot.pause()

    assert BadcaseStore(tmp_path / "badcases.jsonl").read_all()[0]["added_to_eval"] is True


@pytest.mark.asyncio
async def test_default_runtime_factory_receives_live_queue_sink(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp
    from ananhu_agent.runtime import create_default_runtime

    app = AnanhuChatApp(runtime_factory=create_default_runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        for _ in range(8):
            await pilot.pause()
        assert app._events
        if app._running_task is not None:
            await app._running_task


@pytest.mark.asyncio
async def test_feedback_good_confirms_and_bad_persists_legacy_badcase_fields(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test() as pilot:
        await pilot.press("h", "i", "enter")
        await pilot.pause()
        runtime.release.set()
        await pilot.pause()
        await pilot.press("f4")
        await pilot.pause()
        await pilot.click("#feedback-good")
        await pilot.pause()
        assert "已收到正向反馈" in str(app.query_one("#chat-status").render())

        await pilot.press("f4")
        await pilot.pause()
        await pilot.click("#feedback-bad")
        await pilot.pause()
        await pilot.click("#issue-type")
        await pilot.press("4")
        app.screen.query_one("#expected-answer", Input).value = "应核对地方政策"
        app.screen.query_one("#correction-note", Input).value = "地区政策不匹配"
        await pilot.click("#feedback-submit")
        await pilot.pause()
    records = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "region_policy_mismatch" in records
    assert "应核对地方政策" in records
    assert '"request_id"' in records


def _assert_tui_regions(app) -> None:
    """验收屏幕纵向区域不重叠，且主会话区不产生横向滚动。"""

    header = app.query_one("#header").region
    conversation = app.query_one("#conversation").region
    input_region = app.query_one("#chat-input").region
    status = app.query_one("#chat-status").region
    footer = app.query_one("#footer").region

    assert header.bottom <= conversation.y
    assert conversation.bottom <= input_region.y
    assert input_region.bottom <= status.y
    assert status.bottom <= footer.y
    assert app.query_one("#conversation").virtual_size.width <= app.screen.size.width


def _publish_layout_events(app, request) -> None:
    """注入深层树和超宽 JSON，覆盖真实检查器的布局边界。"""

    app._apply_event(NodeStartedEvent(
        run_id=request.run_id,
        request_id=request.request_id,
        session_id=request.session_id,
        node_id="understand",
        sequence_no=2,
        public_payload={
            "phase": "understand",
            "input_summary": {
                "中文问题": "四川十级工伤，月工资6000",
                "long_token": "x" * 120,
            },
        },
    ))
    app._apply_event(ModelFinishedEvent(
        run_id=request.run_id,
        request_id=request.request_id,
        session_id=request.session_id,
        node_id="understand",
        sequence_no=3,
        public_payload=ModelFinishedPayload(
            profile="intent_fast",
            provider="provider",
            model="model",
            output_summary={
                "markdown_table": "| 地区 | 等级 | 金额 |\n| --- | --- | --- |\n| 四川 | 十级 | 6000 |",
                "deep_json": {"level_1": {"level_2": {"level_3": {"token": "y" * 120}}}},
            },
        ),
    ))


@pytest.mark.asyncio
async def test_80x24_regions_do_not_overlap(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press(*"x" * 120, "enter")
        await pilot.pause()
        _assert_tui_regions(app)
        acceptance_dir = tmp_path / ".ananhu-runtime" / "acceptance"
        acceptance_dir.mkdir(parents=True)
        app.save_screenshot(filename="tui-80x24.svg", path=str(acceptance_dir))


@pytest.mark.asyncio
async def test_long_content_does_not_create_page_horizontal_scroll(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("x", "enter")
        await pilot.pause()
        _publish_layout_events(app, runtime.requests[0])
        await pilot.pause()

        _assert_tui_regions(app)
        assert app.query_one("#conversation").virtual_size.width <= app.screen.size.width


@pytest.mark.asyncio
async def test_json_detail_has_local_horizontal_scroll(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("x", "enter")
        await pilot.pause()
        _publish_layout_events(app, runtime.requests[0])
        inspector = app.query_one("#run-inspector")
        item = inspector.model.item("understand.input")
        inspector._show_detail(item)
        await pilot.pause()

        assert str(inspector.query_one("#json-detail").styles.overflow_x) == "auto"


@pytest.mark.asyncio
async def test_resize_during_run_preserves_regions_and_input(tmp_path):
    from ananhu_agent.cli.tui.app import AnanhuChatApp

    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("x", "enter")
        await pilot.pause()
        assert app.input_area.disabled is True
        _assert_tui_regions(app)

        await pilot.resize_terminal(100, 30)
        await pilot.pause()
        _assert_tui_regions(app)

        await pilot.resize_terminal(80, 24)
        await pilot.pause()
        _assert_tui_regions(app)
        assert app.input_area.disabled is True
        acceptance_dir = tmp_path / ".ananhu-runtime" / "acceptance"
        acceptance_dir.mkdir(parents=True)
        app.save_screenshot(filename="tui-resized.svg", path=str(acceptance_dir))
        runtime.release.set()
