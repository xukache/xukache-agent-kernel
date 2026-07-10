from __future__ import annotations

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.infrastructure.models.fake import FakeModelGateway
from ananhu_agent.models.observable_gateway import ObservableModelGateway
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


def test_both_runtime_compositions_use_project_model_gateway(tmp_path):
    native = create_default_runtime(
        tmp_path / "native",
        RuntimeSettings(runtime="native", runtime_dir=tmp_path / "native"),
    )
    langgraph = create_default_runtime(
        tmp_path / "langgraph",
        RuntimeSettings(runtime="langgraph", runtime_dir=tmp_path / "langgraph"),
    )

    assert isinstance(native.intent_agent.model_gateway, ObservableModelGateway)
    assert isinstance(langgraph.intent_agent.model_gateway, ObservableModelGateway)
    assert isinstance(native.intent_agent.model_gateway.inner, FakeModelGateway)
    assert isinstance(langgraph.intent_agent.model_gateway.inner, FakeModelGateway)
