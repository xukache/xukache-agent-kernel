from __future__ import annotations

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.runtimes.langgraph.runtime import LangGraphWorkflowRuntime
from ananhu_agent.runtimes.native.runtime import NativeWorkflowRuntime


def test_default_runtime_is_langgraph(tmp_path):
    runtime = create_default_runtime(tmp_path)

    assert isinstance(runtime, LangGraphWorkflowRuntime)


def test_runtime_setting_can_explicitly_select_native(tmp_path):
    runtime = create_default_runtime(
        tmp_path,
        RuntimeSettings(runtime_dir=tmp_path, runtime="native"),
    )

    assert isinstance(runtime, NativeWorkflowRuntime)


def test_runtime_can_be_selected_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME", "native")

    runtime = create_default_runtime(tmp_path)

    assert isinstance(runtime, NativeWorkflowRuntime)
