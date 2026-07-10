"""框架中立工作流协议入口。"""

from ananhu_agent.workflow.contracts import (
    SCHEMA_VERSION,
    RunRequest,
    RunStatus,
    StatePatch,
    StopReason,
    WorkflowPhase,
    WorkflowResult,
    WorkflowState,
)
from ananhu_agent.workflow.reducer import ReducerResult, reduce_workflow_state

__all__ = [
    "SCHEMA_VERSION",
    "RunRequest",
    "RunStatus",
    "StatePatch",
    "StopReason",
    "WorkflowPhase",
    "WorkflowResult",
    "WorkflowState",
    "ReducerResult",
    "reduce_workflow_state",
]
