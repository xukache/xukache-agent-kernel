from pathlib import Path
from typing import Any

from ananhu_agent.schemas import BadcaseRecord, RunReport, SessionState, TaskState, TraceEvent
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


class SessionStateStore:
    """多轮 CLI 会话状态存储。

    SessionState 回答“同一 session 上一轮留下了什么上下文”，只服务于编排器恢复会话记忆。
    """

    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def append(self, state: SessionState) -> None:
        self.store.append(state)

    def read_all(self) -> list[dict[str, Any]]:
        return self.store.read_all()

    def get_latest(self, session_id: str) -> SessionState | None:
        """按追加顺序返回指定 session 的最新状态。"""
        for row in reversed(self.read_all()):
            if row["session_id"] == session_id:
                return SessionState(**row)
        return None


class BadcaseStore:
    """用户反馈和系统自动分流的 badcase 存储。"""

    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def append(self, record: BadcaseRecord) -> None:
        self.store.append(record)

    def read_all(self) -> list[dict[str, Any]]:
        return self.store.read_all()
