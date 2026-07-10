from __future__ import annotations

import inspect

from ananhu_agent.cli import main as cli_main
from ananhu_agent.evaluation.runner import EvalRunner
from ananhu_agent.workflow.contracts import WorkflowRuntime


def test_eval_runner_depends_on_workflow_runtime_port():
    signature = inspect.signature(EvalRunner.__init__)

    assert signature.parameters["runtime"].annotation == "WorkflowRuntime"


def test_cli_ask_and_eval_use_runtime_composition_root():
    source = inspect.getsource(cli_main)

    assert "create_default_runtime" in source
    assert "create_default_orchestrator" not in source
    assert "WorkflowRuntime" in source
