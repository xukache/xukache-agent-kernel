from __future__ import annotations

import asyncio

import pytest

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.workflow.contracts import RunRequest, RunStatus


def _request(query: str, *, run_id: str) -> RunRequest:
    return RunRequest(
        run_id=run_id,
        request_id=f"req_{run_id}",
        session_id="other-intent-contract",
        turn_id=1,
        user_query=query,
        created_at="2026-07-10T00:00:00+08:00",
    )


def _invoke_with_events(tmp_path, runtime_name: str, query: str):
    runtime = create_default_runtime(
        tmp_path,
        RuntimeSettings(runtime_dir=tmp_path, runtime=runtime_name),
    )
    result = asyncio.run(runtime.invoke(_request(query, run_id=f"run_{runtime_name}")))
    return result, runtime.trace_recorder.read_all()


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_greeting_returns_exact_capability_message_without_tools(tmp_path, runtime_name):
    result, events = _invoke_with_events(tmp_path, runtime_name, "你好")

    assert result.final_answer == (
        "你好，我是安安虎工伤咨询助手。你可以咨询工伤认定、劳动能力鉴定和待遇测算问题。"
    )
    assert result.status is RunStatus.COMPLETED
    assert not [event for event in events if event["event_type"].startswith("capability_")]
    assert not [event for event in events if event["event_type"].startswith("tool_")]


@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_non_domain_other_invites_rewrite_without_tools(tmp_path, runtime_name):
    result, events = _invoke_with_events(tmp_path, runtime_name, "你会写代码吗？")

    assert result.final_answer is not None
    assert "请改写为工伤相关问题" in result.final_answer
    assert not [event for event in events if event["event_type"].startswith("capability_")]
    assert not [event for event in events if event["event_type"].startswith("tool_")]
