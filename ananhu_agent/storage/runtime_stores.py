from pathlib import Path
from typing import Any

from ananhu_agent.schemas import RunReport, TaskState, TraceEvent
from ananhu_agent.storage.jsonl_store import JsonlStore


class TraceRecorder:
    """trace 事件写入器。

    Orchestrator、ToolExecutor、PromptManager 等运行时组件后续都应通过该封装记录
    TraceEvent，而不是直接操作 JSONL 文件路径。
    """

    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def record(self, event: TraceEvent) -> None:
        self.store.append(event)

    def read_all(self) -> list[dict[str, Any]]:
        return self.store.read_all()


class TaskStateStore:
    """单轮任务状态快照存储。

    TaskState 回答“当前轮跑到哪一步”，用于恢复、诊断和 badcase 分流。
    """

    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def append(self, state: TaskState) -> None:
        self.store.append(state)

    def read_all(self) -> list[dict[str, Any]]:
        return self.store.read_all()


class ReportStore:
    """单轮运行报告存储。

    RunReport 是评测、运营统计和问题复盘使用的摘要证据，不替代逐事件 trace。
    """

    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def append(self, report: RunReport) -> None:
        self.store.append(report)

    def read_all(self) -> list[dict[str, Any]]:
        return self.store.read_all()
