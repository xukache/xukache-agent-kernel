# 安安虎 Agno CLI MVP Agent Harness 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 按当前架构文档实现一个无 HTTP、无前端的工伤智能助手 CLI MVP，跑通“用户输入 -> 意图识别 -> Agent 路由 -> RAG / 测算工具 -> 聚合校验 -> CLI 输出 -> Trace / Badcase / Eval”的最小闭环。

**架构：** 以 `AgentOrchestrator` 作为唯一状态推进方，4 个 MVP Agent 均保持无状态，只通过 `AgentContext` 读取输入并返回结构化 `AgentMessage`。所有 Prompt 经 `PromptManager` 和 `ContextManager` 构造，所有工具经 `ToolRegistry` 和 `ToolExecutor` 执行，所有关键事件写入 `TraceRecorder`、`TaskStateStore` 和 `ReportStore`。

**技术栈：** Python 3.11、uv、Pydantic、Typer、pytest、PyYAML、Agno（Agent 接入阶段）、本地 JSONL 存储、本地 fixture RAG 数据。

---

## 0. 计划依据与第一性原理

本计划依据：

- `docs/architecture.md`
- `docs/architecture/00-overview.md`
- `docs/architecture/01-business-flow.md`
- `docs/architecture/02-agent-runtime.md`
- `docs/architecture/03-prompt-context.md`
- `docs/architecture/04-tools-models.md`
- `docs/architecture/05-data-observability.md`
- `docs/architecture/10-evolution-rules.md`
- `docs/backend-conventions.md`
- `docs/api-contracts.md`
- `AGENTS.md`

第一性原理拆解：

1. 一个可工作的 Agent 系统首先需要稳定协议，而不是先写模型调用；所以先实现 `AgentContext`、`AgentMessage`、槽位、trace、tool result 等 schema。
2. 政务咨询必须可追踪、可回放、可评测；所以 trace、task state、report 不是附属日志，而是与运行时同级的 P0 能力。
3. Agent 不能直接写状态、不能直接调用工具、不能硬编码 prompt；所以 Orchestrator、ToolExecutor、PromptManager、ContextManager 必须先于业务 Agent。
4. MVP 的价值来自完整闭环，而不是 Agent 数量；所以每个阶段都必须产出可运行或可测试的垂直切片。
5. 当前项目没有代码结构；所以第 1 阶段必须先建立最小 Python 工程、测试命令和 fixtures。

## 1. 文件结构

创建以下代码与数据文件：

- `.python-version`：固定 Python 版本为 3.11。
- `pyproject.toml`：Python 包、依赖、pytest 配置、console script。
- `ananhu_agent/__init__.py`：包版本。
- `ananhu_agent/schemas.py`：所有跨模块协议 schema。
- `ananhu_agent/config/settings.py`：Pydantic settings 与本地路径配置。
- `ananhu_agent/storage/jsonl_store.py`：JSONL 读写基础设施。
- `ananhu_agent/storage/runtime_stores.py`：TaskState、Trace、Report、Badcase、Eval 存储封装。
- `ananhu_agent/context/slot_rules.py`：槽位合并、缺失槽位判断、地区继承保护。
- `ananhu_agent/context/context_manager.py`：上下文分段、排序、裁剪和 metadata。
- `ananhu_agent/prompts/prompt_manager.py`：Prompt 模板加载、版本选择、分区渲染。
- `ananhu_agent/prompts/templates/*.yaml`：MVP prompt 元信息和模板。
- `ananhu_agent/tools/registry.py`：工具注册表。
- `ananhu_agent/tools/executor.py`：工具权限、schema、超时、错误归一、trace。
- `ananhu_agent/tools/policy_rag.py`：本地 fixture RAG 检索工具。
- `ananhu_agent/tools/payment_calculation.py`：工伤待遇测算工具。
- `ananhu_agent/tools/formatters.py`：地区过滤和引用格式化工具。
- `ananhu_agent/models/model_router.py`：model profile 到 client 的路由。
- `ananhu_agent/models/fake_model.py`：测试用确定性模型。
- `ananhu_agent/agents/intent_router.py`：意图识别、槽位抽取、低置信度追问。
- `ananhu_agent/agents/policy_rag.py`：政策依据检索和证据组织。
- `ananhu_agent/agents/domain_consultation.py`：工伤认定、劳动能力鉴定、参保认定文本咨询。
- `ananhu_agent/agents/payment_calculation.py`：待遇测算解释和工具调用。
- `ananhu_agent/orchestrator/rules.py`：`IntentReviseRule`、`SlotMergeRule`。
- `ananhu_agent/orchestrator/aggregator.py`：草稿答案与最终答案聚合。
- `ananhu_agent/orchestrator/validators.py`：依据、地区一致性、输出结构校验。
- `ananhu_agent/orchestrator/safety.py`：政务安全表达守卫。
- `ananhu_agent/orchestrator/orchestrator.py`：单轮同步主流程。
- `ananhu_agent/cli/main.py`：交互式 CLI、单轮 ask、eval 命令。
- `ananhu_agent/evaluation/runner.py`：eval case 执行。
- `ananhu_agent/evaluation/metrics.py`：规则型指标计算。
- `data/policies/policy_fixtures.jsonl`：MVP 法规与地方政策样例。
- `data/eval/eval_cases.jsonl`：MVP 评测样例。
- `tests/`：按模块建立单元测试和 CLI 垂直切片测试。

修改以下文档：

- `docs/backend-conventions.md`：实现后补充安装、运行、测试命令。
- `docs/architecture/99-changelog.md`：记录从架构基线进入代码实现的事实变更。

## 2. 阶段与依赖图

| 阶段 | 目标 | 依赖 | 可验收结果 |
|---|---|---|---|
| P1 | 建立 Python 工程与测试入口 | 无 | `pytest` 能运行，CLI 包入口存在 |
| P2 | 定义协议与本地证据存储 | P1 | schema 单测通过，trace/report 可写入 JSONL |
| P3 | 实现上下文、Prompt、模型路由 | P2 | prompt 可渲染，context 可裁剪且不裁剪当前问题 |
| P4 | 实现 ToolRegistry、ToolExecutor 和 MVP 工具 | P2、P3 | RAG、测算、引用工具均经 executor 调用并写 trace |
| P5 | 实现 4 个 Agent 与 Orchestrator 垂直链路 | P2、P3、P4 | CLI 可回答工伤认定、劳动能力鉴定、待遇测算 |
| P6 | 实现 eval、badcase 和文档同步 | P5 | `/eval` 产出 metrics，失败样例写 badcase |

依赖规则：

- P2 不依赖 P3，因为 schema 和存储必须先稳定。
- P4 不依赖 P5，因为工具治理必须先于 Agent 调用。
- P5 不允许绕过 P4 直接调用工具函数。
- P6 只依赖 P5 的完整单轮链路，不反向影响前面协议。

## 3. 任务清单

### 任务 1：初始化 Python 工程骨架

**目标：** 建立可安装、可测试、可执行 CLI 的最小工程。

**涉及模块：** 工程配置、包入口、CLI 入口。

**前置依赖：** 无。

**文件：**
- 复用：`.python-version`
- 创建：`.gitignore`
- 创建：`pyproject.toml`
- 创建：`uv.lock`
- 创建：`ananhu_agent/__init__.py`
- 创建：`ananhu_agent/cli/__init__.py`
- 创建：`ananhu_agent/cli/main.py`
- 创建：`tests/test_package_bootstrap.py`

- [x] **步骤 1：编写失败的包启动测试**

创建 `tests/test_package_bootstrap.py`：

```python
from typer.testing import CliRunner

from ananhu_agent import __version__
from ananhu_agent.cli.main import app


def test_package_has_version():
    assert __version__ == "0.1.0"


def test_cli_version_command():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ananhu-agent 0.1.0" in result.output
```

- [x] **步骤 2：运行测试验证失败**

运行：

```bash
uv run --with pytest --with typer pytest tests/test_package_bootstrap.py -v
```

预期：FAIL，报错包含 `ModuleNotFoundError: No module named 'ananhu_agent'`。

- [x] **步骤 3：创建最小包和 CLI**

创建 `.python-version`：

```text
3.11
```

创建 `pyproject.toml`：

```toml
[project]
name = "ananhu-agent-agno"
version = "0.1.0"
description = "Ananhu work injury consultation CLI multi-agent MVP"
requires-python = ">=3.11,<3.12"
dependencies = [
  "pydantic>=2.7",
  "pydantic-settings>=2.2",
  "typer>=0.12",
  "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
]

[project.scripts]
ananhu-agent = "ananhu_agent.cli.main:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.uv]
package = true
```

创建 `ananhu_agent/__init__.py`：

```python
__version__ = "0.1.0"
```

创建 `ananhu_agent/cli/__init__.py`：

```python
```

创建 `ananhu_agent/cli/main.py`：

```python
import typer

from ananhu_agent import __version__

app = typer.Typer(help="安安虎工伤智能助手 CLI MVP")


@app.callback()
def main() -> None:
    """安安虎工伤智能助手 CLI MVP."""


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(f"ananhu-agent {__version__}")
```

- [x] **步骤 4：运行测试验证通过**

运行：

```bash
uv sync --extra dev
uv run pytest tests/test_package_bootstrap.py -v
```

预期：2 passed。

- [x] **步骤 5：提交**

```bash
git add .gitignore pyproject.toml uv.lock ananhu_agent tests/test_package_bootstrap.py docs/superpowers/plans/2026-07-09-cli-mvp-agent-harness.md
git commit -m "chore: initialize cli python package"
```

**验收标准：**

- `uv run pytest tests/test_package_bootstrap.py -v` 通过。
- `uv run pytest -v` 通过，当前为 2 passed。
- `uv run ananhu-agent version` 输出 `ananhu-agent 0.1.0`。
- `CliRunner().invoke(app, ["version"])` 能验证 Typer 命令；不要用 `python -m ananhu_agent.cli.main version` 作为验收，除非同时补 `if __name__ == "__main__": app()`。

### 任务 2：定义运行时协议 schema

**目标：** 固化 Agent、Tool、Trace、TaskState、Report、Eval 的跨模块协议，后续任务只能依赖这些结构。

**涉及模块：** schema、运行时协议。

**前置依赖：** 任务 1。

**文件：**
- 创建：`ananhu_agent/schemas.py`
- 创建：`tests/test_schemas.py`

- [x] **步骤 1：编写失败的 schema 测试**

创建 `tests/test_schemas.py`：

```python
from ananhu_agent.schemas import (
    AgentContext,
    AgentMessage,
    RunReport,
    RequestContext,
    TaskState,
    ToolCallResult,
    TraceEvent,
)


def test_agent_context_contains_required_runtime_sections():
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤大概能赔多少钱？",
        province="四川省",
        city="成都市",
    )

    assert ctx.request.user_query == "四川十级工伤大概能赔多少钱？"
    assert ctx.intent_result is None
    assert ctx.tool_results == []
    assert ctx.agent_outputs == []
    assert ctx.final_answer is None


def test_agent_message_is_structured():
    message = AgentMessage(
        agent_name="IntentRouterAgent",
        status="success",
        content="识别为待遇测算",
        data={"intent": "payment_calculation"},
        tool_calls=[],
        missing_slots=[],
        citations=[],
        warnings=[],
    )

    assert message.agent_name == "IntentRouterAgent"
    assert message.data["intent"] == "payment_calculation"


def test_tool_call_result_and_trace_event_are_serializable():
    request = RequestContext.new(
        session_id="sess_1",
        turn_id=1,
        user_query="劳动能力鉴定要什么材料？",
    )
    result = ToolCallResult(
        tool_call_id="tool_001",
        tool_name="PolicyRAGTool",
        called_by="PolicyRAGAgent",
        tool_status="success",
        tool_error_code=None,
        latency_ms=12,
        input={"query": request.user_query},
        output={"documents": []},
        fallback_used=False,
    )
    event = TraceEvent.new(
        request_id=request.request_id,
        session_id=request.session_id,
        event_type="tool_finished",
        phase="tool",
        payload=result.model_dump(),
        latency_ms=12,
    )

    assert event.payload["tool_name"] == "PolicyRAGTool"
    assert event.created_at.endswith("+08:00")


def test_task_state_and_run_report_capture_runtime_evidence():
    state = TaskState(
        id="state_1",
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤大概能赔多少钱？",
        status="completed",
        current_phase="response_ready",
        raw_intent="payment_calculation",
        revised_intent="payment_calculation",
        active_slots={"province": "四川省"},
        missing_slots=[],
        route_agents=["PaymentCalculationAgent", "PolicyRAGAgent"],
        prompt_refs=["intent_router.v1"],
        tool_steps=["PaymentCalculationTool", "PolicyRAGTool"],
        model_attempts=1,
        fallback_used=False,
        error_message=None,
    )
    report = RunReport(
        id="report_1",
        session_id="sess_1",
        final_status="success",
        final_intent="payment_calculation",
        route_agents=["PaymentCalculationAgent", "PolicyRAGAgent"],
        tool_count=2,
        model_attempts=1,
        prompt_refs=["intent_router.v1"],
        prompt_metadata={"intent_router.v1": {"version": "v1"}},
        output_schema_valid_rate=1.0,
        token_usage={},
        latency_ms=10,
        fallback_used=False,
        safety_result={"passed": True},
        badcase_candidate=False,
    )

    assert state.current_phase == "response_ready"
    assert report.tool_count == 2
```

- [x] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_schemas.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.schemas'`。

- [x] **步骤 3：实现最小 schema**

创建 `ananhu_agent/schemas.py`，至少包含：

```python
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

CN_TZ = timezone(timedelta(hours=8))


def now_cn() -> str:
    return datetime.now(CN_TZ).isoformat(timespec="seconds")


class RequestContext(BaseModel):
    request_id: str
    session_id: str
    turn_id: int
    user_query: str
    input_type: Literal["text"] = "text"
    province: str | None = None
    city: str | None = None
    created_at: str

    @classmethod
    def new(
        cls,
        session_id: str,
        turn_id: int,
        user_query: str,
        province: str | None = None,
        city: str | None = None,
    ) -> "RequestContext":
        return cls(
            request_id=f"req_{uuid4().hex[:12]}",
            session_id=session_id,
            turn_id=turn_id,
            user_query=user_query,
            province=province,
            city=city,
            created_at=now_cn(),
        )


class ConversationState(BaseModel):
    history_summary: str = ""
    last_user_intent: str | None = None
    last_answer_summary: str = ""
    active_slots: dict[str, Any] = Field(default_factory=dict)


class IntentResult(BaseModel):
    intent: str
    confidence: float
    slots: dict[str, Any] = Field(default_factory=dict)
    is_composite: bool = False
    missing_slots: list[str] = Field(default_factory=list)
    ask_clarification: str | None = None


class AgentPlan(BaseModel):
    route_agents: list[str]
    required_tools: list[str] = Field(default_factory=list)
    execution_mode: Literal["sync_serial"] = "sync_serial"


class ToolCallRequest(BaseModel):
    tool_call_id: str
    tool_name: str
    called_by: str
    input: dict[str, Any]


class ToolCallResult(BaseModel):
    tool_call_id: str
    tool_name: str
    called_by: str
    tool_status: Literal["success", "failed"]
    tool_error_code: str | None
    latency_ms: int
    input: dict[str, Any]
    output: dict[str, Any]
    fallback_used: bool = False


class AgentMessage(BaseModel):
    agent_name: str
    status: Literal["success", "failed", "need_clarification"]
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)


class SafetyResult(BaseModel):
    passed: bool
    warnings: list[str] = Field(default_factory=list)


class TaskState(BaseModel):
    id: str
    session_id: str
    turn_id: int
    user_query: str
    status: str
    current_phase: str
    raw_intent: str | None = None
    revised_intent: str | None = None
    active_slots: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    route_agents: list[str] = Field(default_factory=list)
    prompt_refs: list[str] = Field(default_factory=list)
    tool_steps: list[str] = Field(default_factory=list)
    model_attempts: int = 0
    fallback_used: bool = False
    error_message: str | None = None


class RunReport(BaseModel):
    id: str
    session_id: str
    final_status: str
    final_intent: str | None
    route_agents: list[str]
    tool_count: int
    model_attempts: int
    prompt_refs: list[str]
    prompt_metadata: dict[str, Any]
    output_schema_valid_rate: float
    token_usage: dict[str, Any]
    latency_ms: int
    fallback_used: bool
    safety_result: dict[str, Any]
    badcase_candidate: bool


class AgentContext(BaseModel):
    request: RequestContext
    conversation: ConversationState = Field(default_factory=ConversationState)
    intent_result: IntentResult | None = None
    agent_plan: AgentPlan | None = None
    tool_results: list[ToolCallResult] = Field(default_factory=list)
    agent_outputs: list[AgentMessage] = Field(default_factory=list)
    draft_final_answer: str | None = None
    verification_result: VerificationResult | None = None
    safety_result: SafetyResult | None = None
    final_answer: str | None = None

    @classmethod
    def new_for_query(
        cls,
        session_id: str,
        turn_id: int,
        user_query: str,
        province: str | None = None,
        city: str | None = None,
    ) -> "AgentContext":
        return cls(
            request=RequestContext.new(
                session_id=session_id,
                turn_id=turn_id,
                user_query=user_query,
                province=province,
                city=city,
            )
        )


class TraceEvent(BaseModel):
    id: str
    request_id: str
    session_id: str
    event_type: str
    phase: str
    payload: dict[str, Any]
    latency_ms: int | None = None
    created_at: str

    @classmethod
    def new(
        cls,
        request_id: str,
        session_id: str,
        event_type: str,
        phase: str,
        payload: dict[str, Any],
        latency_ms: int | None = None,
    ) -> "TraceEvent":
        return cls(
            id=f"trace_{uuid4().hex[:12]}",
            request_id=request_id,
            session_id=session_id,
            event_type=event_type,
            phase=phase,
            payload=payload,
            latency_ms=latency_ms,
            created_at=now_cn(),
        )
```

- [x] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_schemas.py -v
```

预期：4 passed。

- [x] **步骤 5：提交**

```bash
git add ananhu_agent/schemas.py tests/test_schemas.py
git commit -m "feat: define runtime schemas"
```

**验收标准：**

- schema 覆盖 `AgentContext`、`AgentMessage`、`ToolCallRequest`、`ToolCallResult`、`TraceEvent`、`TaskState`、`RunReport`。
- 后续任务不得新增与这些重复的并行协议。

### 任务 3：实现 JSONL 证据存储

**目标：** 让 trace、report、badcase、eval 输出都有本地可回放证据。

**涉及模块：** `storage`、运行证据。

**前置依赖：** 任务 2。

**文件：**
- 创建：`ananhu_agent/storage/__init__.py`
- 创建：`ananhu_agent/storage/jsonl_store.py`
- 创建：`ananhu_agent/storage/runtime_stores.py`
- 创建：`tests/test_storage.py`

- [x] **步骤 1：编写失败测试**

创建 `tests/test_storage.py`：

```python
from ananhu_agent.schemas import RunReport, TaskState, TraceEvent
from ananhu_agent.storage.runtime_stores import ReportStore, TaskStateStore, TraceRecorder


def test_trace_recorder_appends_jsonl(tmp_path):
    recorder = TraceRecorder(tmp_path / "traces.jsonl")
    event = TraceEvent.new(
        request_id="req_1",
        session_id="sess_1",
        event_type="request_received",
        phase="orchestrator",
        payload={"user_query": "上班路上交通事故算工伤吗？"},
    )

    recorder.record(event)
    rows = recorder.read_all()

    assert len(rows) == 1
    assert rows[0]["event_type"] == "request_received"
    assert rows[0]["payload"]["user_query"] == "上班路上交通事故算工伤吗？"


def test_task_state_and_report_store_append_runtime_evidence(tmp_path):
    task_store = TaskStateStore(tmp_path / "task_states.jsonl")
    report_store = ReportStore(tmp_path / "run_reports.jsonl")
    task_store.append(
        TaskState(
            id="state_1",
            session_id="sess_1",
            turn_id=1,
            user_query="劳动能力鉴定需要准备哪些材料？",
            status="completed",
            current_phase="response_ready",
        )
    )
    report_store.append(
        RunReport(
            id="report_1",
            session_id="sess_1",
            final_status="success",
            final_intent="labor_capacity",
            route_agents=["DomainConsultationAgent", "PolicyRAGAgent"],
            tool_count=1,
            model_attempts=1,
            prompt_refs=["intent_router.v1"],
            prompt_metadata={},
            output_schema_valid_rate=1.0,
            token_usage={},
            latency_ms=8,
            fallback_used=False,
            safety_result={"passed": True},
            badcase_candidate=False,
        )
    )

    assert task_store.read_all()[0]["current_phase"] == "response_ready"
    assert report_store.read_all()[0]["final_intent"] == "labor_capacity"
```

- [x] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_storage.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.storage'`。

- [x] **步骤 3：实现 JSONLStore 和 TraceRecorder**

创建 `ananhu_agent/storage/__init__.py`：

```python
```

创建 `ananhu_agent/storage/jsonl_store.py`：

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class JsonlStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, row: BaseModel | dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = row.model_dump() if isinstance(row, BaseModel) else row
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
```

创建 `ananhu_agent/storage/runtime_stores.py`：

```python
from pathlib import Path

from ananhu_agent.schemas import RunReport, TaskState, TraceEvent
from ananhu_agent.storage.jsonl_store import JsonlStore


class TraceRecorder:
    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def record(self, event: TraceEvent) -> None:
        self.store.append(event)

    def read_all(self) -> list[dict]:
        return self.store.read_all()


class TaskStateStore:
    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def append(self, state: TaskState) -> None:
        self.store.append(state)

    def read_all(self) -> list[dict]:
        return self.store.read_all()


class ReportStore:
    def __init__(self, path: Path) -> None:
        self.store = JsonlStore(path)

    def append(self, report: RunReport) -> None:
        self.store.append(report)

    def read_all(self) -> list[dict]:
        return self.store.read_all()
```

- [x] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_storage.py -v
```

预期：2 passed。

- [x] **步骤 5：提交**

```bash
git add ananhu_agent/storage tests/test_storage.py
git commit -m "feat: add jsonl trace storage"
```

**验收标准：**

- trace、task state、run report 能写入并读回。
- JSONL 文件使用 UTF-8，中文不转义。

### 任务 4：实现槽位合并与路由修正规则

**目标：** 让低置信度追问、强关键词修正、地区继承和地区覆盖都有确定性规则。

**涉及模块：** `context`、`orchestrator/rules`。

**前置依赖：** 任务 2。

**文件：**
- 创建：`ananhu_agent/context/__init__.py`
- 创建：`ananhu_agent/context/slot_rules.py`
- 创建：`ananhu_agent/orchestrator/__init__.py`
- 创建：`ananhu_agent/orchestrator/rules.py`
- 创建：`tests/test_intent_rules.py`

- [x] **步骤 1：编写失败测试**

创建 `tests/test_intent_rules.py`：

```python
from ananhu_agent.context.slot_rules import merge_slots
from ananhu_agent.orchestrator.rules import revise_intent
from ananhu_agent.schemas import IntentResult


def test_payment_keyword_overrides_low_value_intent():
    result = IntentResult(intent="policy_consultation", confidence=0.7)
    revised = revise_intent("四川十级工伤大概能赔多少钱？", result)

    assert revised.intent == "payment_calculation"


def test_low_confidence_with_missing_slots_asks_clarification():
    result = IntentResult(
        intent="work_injury_recognition",
        confidence=0.4,
        missing_slots=["accident_type"],
    )
    revised = revise_intent("这个能不能算？", result)

    assert revised.ask_clarification == "请补充事故场景、发生时间、地区和责任划分。"


def test_current_region_overrides_history_region():
    merged, metadata = merge_slots(
        history={"province": "四川省", "city": "成都市"},
        current={"province": "辽宁省", "city": "丹东市"},
    )

    assert merged["province"] == "辽宁省"
    assert metadata["region_overridden"] is True
```

- [x] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_intent_rules.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.context'`。

- [x] **步骤 3：实现规则**

创建 `ananhu_agent/context/__init__.py` 和 `ananhu_agent/orchestrator/__init__.py` 为空文件。

创建 `ananhu_agent/context/slot_rules.py`：

```python
from typing import Any


def merge_slots(
    history: dict[str, Any],
    current: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, bool]]:
    merged = {**history, **{k: v for k, v in current.items() if v not in (None, "")}}
    metadata = {
        "region_inherited": False,
        "region_overridden": False,
    }
    if "province" not in current and "province" in history:
        metadata["region_inherited"] = True
    if current.get("province") and history.get("province") and current["province"] != history["province"]:
        metadata["region_overridden"] = True
    return merged, metadata
```

创建 `ananhu_agent/orchestrator/rules.py`：

```python
from ananhu_agent.schemas import IntentResult

PAYMENT_KEYWORDS = ("赔多少钱", "待遇", "一次性伤残补助金", "医疗补助金")
RECOGNITION_KEYWORDS = ("算不算工伤", "能不能认定", "上下班途中", "非本人主要责任")
LABOR_CAPACITY_KEYWORDS = ("劳动能力鉴定", "伤残等级", "鉴定材料", "复查鉴定")


def revise_intent(user_query: str, result: IntentResult) -> IntentResult:
    data = result.model_copy(deep=True)
    if any(keyword in user_query for keyword in PAYMENT_KEYWORDS):
        data.intent = "payment_calculation"
    elif any(keyword in user_query for keyword in RECOGNITION_KEYWORDS):
        data.intent = "work_injury_recognition"
    elif any(keyword in user_query for keyword in LABOR_CAPACITY_KEYWORDS):
        data.intent = "labor_capacity"

    if data.confidence < 0.6 and data.missing_slots:
        data.ask_clarification = "请补充事故场景、发生时间、地区和责任划分。"

    return data
```

- [x] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_intent_rules.py -v
```

预期：3 passed。

- [x] **步骤 5：提交**

```bash
git add ananhu_agent/context ananhu_agent/orchestrator tests/test_intent_rules.py
git commit -m "feat: add intent revision and slot merge rules"
```

**验收标准：**

- 待遇测算、工伤认定、劳动能力鉴定关键词可修正路由。
- 低置信度和缺槽位时不进入业务 Agent，返回追问。
- 地区继承和覆盖 metadata 可进入 trace。

### 任务 5：实现 PromptManager 与 ContextManager

**目标：** 禁止 Agent 直接拼 prompt，并记录上下文裁剪 metadata。

**涉及模块：** `prompts`、`context`。

**前置依赖：** 任务 2、任务 3。

**文件：**
- 创建：`ananhu_agent/prompts/__init__.py`
- 创建：`ananhu_agent/prompts/prompt_manager.py`
- 创建：`ananhu_agent/prompts/templates/intent_router.v1.yaml`
- 创建：`ananhu_agent/prompts/templates/domain_consultation.work_injury_recognition.yaml`
- 创建：`ananhu_agent/context/context_manager.py`
- 创建：`tests/test_prompt_context.py`

- [x] **步骤 1：编写失败测试**

创建 `tests/test_prompt_context.py`：

```python
from pathlib import Path

from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext


def test_context_manager_never_trims_current_query():
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=1,
        user_query="上班路上发生交通事故，交警认定我不是主要责任，能不能认定工伤？",
    )
    manager = ContextManager(max_chars=30)

    sections, metadata = manager.build_sections(ctx)

    assert sections["current_query"] == ctx.request.user_query
    assert "current_query" not in metadata["trimmed_sections"]


def test_prompt_manager_loads_metadata_and_renders_sections():
    manager = PromptManager(Path("ananhu_agent/prompts/templates"))
    rendered = manager.render(
        prompt_id="domain_consultation.work_injury_recognition",
        sections={"current_query": "上班路上交通事故算工伤吗？"},
    )

    assert rendered.metadata["agent"] == "DomainConsultationAgent"
    assert "[Output Schema]" in rendered.text
    assert "上班路上交通事故算工伤吗？" in rendered.text
```

- [x] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_prompt_context.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.prompts'`。

- [x] **步骤 3：实现 ContextManager、PromptManager 和模板**

创建 `ananhu_agent/context/context_manager.py`：

```python
from ananhu_agent.schemas import AgentContext


class ContextManager:
    def __init__(self, max_chars: int = 4000) -> None:
        self.max_chars = max_chars

    def build_sections(self, ctx: AgentContext) -> tuple[dict[str, str], dict[str, list[str]]]:
        sections = {
            "system_prefix": "你是工伤政策咨询助手，必须基于依据回答。",
            "active_slots": str(ctx.conversation.active_slots),
            "rag_evidence": "",
            "recent_turns": ctx.conversation.history_summary,
            "working_memory": ctx.conversation.last_answer_summary,
            "current_query": ctx.request.user_query,
        }
        trimmed_sections: list[str] = []
        total = sum(len(value) for value in sections.values())
        if total > self.max_chars:
            for key in ("recent_turns", "working_memory", "rag_evidence"):
                if sections[key]:
                    sections[key] = sections[key][: max(0, self.max_chars // 6)]
                    trimmed_sections.append(key)
        return sections, {"trimmed_sections": trimmed_sections}
```

创建 `ananhu_agent/prompts/__init__.py`：

```python
```

创建 `ananhu_agent/prompts/prompt_manager.py`：

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RenderedPrompt:
    metadata: dict[str, Any]
    text: str


class PromptManager:
    def __init__(self, template_dir: Path) -> None:
        self.template_dir = template_dir

    def render(self, prompt_id: str, sections: dict[str, str]) -> RenderedPrompt:
        path = self.template_dir / f"{prompt_id}.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        body = raw["template"]
        for key, value in sections.items():
            body = body.replace("{{ " + key + " }}", value)
        return RenderedPrompt(metadata=raw["metadata"], text=body)
```

创建 `ananhu_agent/prompts/templates/domain_consultation.work_injury_recognition.yaml`：

```yaml
metadata:
  id: domain_consultation.work_injury_recognition
  version: v1
  agent: DomainConsultationAgent
  task_type: work_injury_recognition
  model_profile: domain_reasoning
  output_schema: AgentMessage
  failure_policy:
    missing_evidence: cannot_answer
    missing_required_slot: ask_clarification
    tool_failed: return_error_reason
  change_note: MVP 初始版本
template: |
  [Role / Task]
  你负责回答工伤认定类政策咨询。

  [Rules]
  不得承诺最终认定结果，必须提示以经办机构和正式材料为准。

  [Input Schema]
  用户当前问题、槽位、政策依据。

  [Context]
  {{ current_query }}

  [RAG Evidence / Tool Results]

  [Output Schema]
  返回结论、依据、适用条件、材料建议、风险提示。

  [Failure Policy]
  依据不足时说明无法确定，并追问缺失信息。
```

创建 `ananhu_agent/prompts/templates/intent_router.v1.yaml`：

```yaml
metadata:
  id: intent_router.v1
  version: v1
  agent: IntentRouterAgent
  task_type: intent_routing
  model_profile: intent_fast
  output_schema: AgentMessage
  failure_policy:
    low_confidence: ask_clarification
  change_note: MVP 初始版本
template: |
  [Role / Task]
  识别用户工伤咨询意图并抽取槽位。

  [Rules]
  只能输出合法意图：work_injury_recognition、labor_capacity、insurance_participation、payment_calculation、other。

  [Input Schema]
  当前问题和上下文槽位。

  [Context]
  {{ current_query }}

  [Output Schema]
  intent、confidence、slots、missing_slots、is_composite。

  [Failure Policy]
  置信度低于阈值时返回追问。
```

- [x] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_prompt_context.py -v
```

预期：2 passed。

- [x] **步骤 5：提交**

```bash
git add ananhu_agent/context/context_manager.py ananhu_agent/prompts tests/test_prompt_context.py
git commit -m "feat: add prompt and context managers"
```

**验收标准：**

- `current_query` 不被裁剪。
- Prompt 元信息包含架构文档要求的字段。
- Agent 后续只能通过 `PromptManager.render()` 获取完整 prompt；任务 8 和任务 11 必须把 `ContextManager` / `PromptManager` 接入 `IntentRouterAgent` 和 trace。

### 任务 6：实现 ToolRegistry、ToolExecutor 和工具 trace

**目标：** 所有工具调用都经过统一治理，包含权限、schema、错误码和 trace。

**涉及模块：** `tools`、`storage`、`schemas`。

**前置依赖：** 任务 2、任务 3。

**文件：**
- 创建：`ananhu_agent/tools/__init__.py`
- 创建：`ananhu_agent/tools/registry.py`
- 创建：`ananhu_agent/tools/executor.py`
- 创建：`tests/test_tool_executor.py`

- [x] **步骤 1：编写失败测试**

创建 `tests/test_tool_executor.py`：

```python
from ananhu_agent.schemas import ToolCallRequest
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.tools.executor import ToolExecutor
from ananhu_agent.tools.registry import ToolDefinition, ToolRegistry


def test_tool_executor_rejects_disallowed_caller(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索政策",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            handler=lambda payload: {"documents": []},
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))
    request = ToolCallRequest(
        tool_call_id="tool_1",
        tool_name="PolicyRAGTool",
        called_by="PaymentCalculationAgent",
        input={"query": "工伤认定"},
    )

    result = executor.execute("req_1", "sess_1", request)

    assert result.tool_status == "failed"
    assert result.tool_error_code == "caller_not_allowed"
    assert executor.trace_recorder.read_all()[0]["event_type"] == "tool_failed"


def test_tool_executor_normalizes_handler_exception(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PaymentCalculationTool",
            description="待遇测算",
            risk_level="calculation",
            timeout_ms=3000,
            allowed_callers=["PaymentCalculationAgent"],
            required_input_keys=["monthly_wage"],
            handler=lambda payload: (_ for _ in ()).throw(ValueError("bad wage")),
        )
    )
    executor = ToolExecutor(registry, TraceRecorder(tmp_path / "trace.jsonl"))
    result = executor.execute(
        "req_1",
        "sess_1",
        ToolCallRequest(
            tool_call_id="tool_2",
            tool_name="PaymentCalculationTool",
            called_by="PaymentCalculationAgent",
            input={"monthly_wage": 6000},
        ),
    )

    assert result.tool_status == "failed"
    assert result.tool_error_code == "tool_handler_error"
```

- [x] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_tool_executor.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.tools'`。

- [x] **步骤 3：实现 registry 和 executor**

创建 `ananhu_agent/tools/__init__.py`：

```python
```

创建 `ananhu_agent/tools/registry.py`：

```python
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: str
    timeout_ms: int
    allowed_callers: list[str]
    required_input_keys: list[str]
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)
```

创建 `ananhu_agent/tools/executor.py`：

```python
from time import perf_counter

from ananhu_agent.schemas import ToolCallRequest, ToolCallResult, TraceEvent
from ananhu_agent.storage.runtime_stores import TraceRecorder
from ananhu_agent.tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, trace_recorder: TraceRecorder) -> None:
        self.registry = registry
        self.trace_recorder = trace_recorder

    def execute(
        self,
        request_id: str,
        session_id: str,
        request: ToolCallRequest,
    ) -> ToolCallResult:
        started = perf_counter()
        definition = self.registry.get(request.tool_name)
        if definition is None:
            return self._fail(request_id, session_id, request, "tool_not_registered", started)
        if request.called_by not in definition.allowed_callers:
            return self._fail(request_id, session_id, request, "caller_not_allowed", started)
        missing = [key for key in definition.required_input_keys if key not in request.input]
        if missing:
            return self._fail(request_id, session_id, request, "invalid_input_schema", started)

        try:
            output = definition.handler(request.input)
        except Exception:
            return self._fail(request_id, session_id, request, "tool_handler_error", started)
        result = ToolCallResult(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            called_by=request.called_by,
            tool_status="success",
            tool_error_code=None,
            latency_ms=int((perf_counter() - started) * 1000),
            input=request.input,
            output=output,
            fallback_used=False,
        )
        self.trace_recorder.record(
            TraceEvent.new(
                request_id=request_id,
                session_id=session_id,
                event_type="tool_finished",
                phase="tool",
                payload=result.model_dump(),
                latency_ms=result.latency_ms,
            )
        )
        return result

    def _fail(
        self,
        request_id: str,
        session_id: str,
        request: ToolCallRequest,
        code: str,
        started: float,
    ) -> ToolCallResult:
        result = ToolCallResult(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            called_by=request.called_by,
            tool_status="failed",
            tool_error_code=code,
            latency_ms=int((perf_counter() - started) * 1000),
            input=request.input,
            output={},
            fallback_used=True,
        )
        self.trace_recorder.record(
            TraceEvent.new(
                request_id=request_id,
                session_id=session_id,
                event_type="tool_failed",
                phase="tool",
                payload=result.model_dump(),
                latency_ms=result.latency_ms,
            )
        )
        return result
```

- [x] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_tool_executor.py -v
```

预期：2 passed。

- [x] **步骤 5：提交**

```bash
git add ananhu_agent/tools tests/test_tool_executor.py
git commit -m "feat: add governed tool executor"
```

**验收标准：**

- 未注册工具、无权限调用、缺少必填输入、handler 异常均返回结构化失败。
- 成功与失败工具调用都进入 trace。
- 后续 Agent 不允许直接调用工具 handler。
- 超时控制和输出 schema 校验如未在本任务落地，必须在真实 RAG / 真实模型接入前补任务；MVP 至少不得把工具异常泄露给最终用户。

### 任务 7：实现本地 PolicyRAGTool、PaymentCalculationTool 和引用格式化

**目标：** 用本地 fixture 数据完成政策检索、待遇测算和依据格式化，避免 MVP 被外部向量库阻塞。

**涉及模块：** `tools`、`data`。

**前置依赖：** 任务 6。

**文件：**
- 创建：`data/policies/policy_fixtures.jsonl`
- 创建：`ananhu_agent/tools/policy_rag.py`
- 创建：`ananhu_agent/tools/payment_calculation.py`
- 创建：`ananhu_agent/tools/formatters.py`
- 创建：`tests/test_mvp_tools.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_mvp_tools.py`：

```python
from pathlib import Path

from ananhu_agent.tools.formatters import format_citations
from ananhu_agent.tools.payment_calculation import calculate_payment
from ananhu_agent.tools.policy_rag import search_policy


def test_policy_rag_returns_grounded_fixture_documents():
    result = search_policy(
        {
            "query": "上下班途中交通事故能不能认定工伤",
            "province": "四川省",
            "city": "成都市",
            "top_k": 3,
            "fixture_path": Path("data/policies/policy_fixtures.jsonl"),
        }
    )

    assert result["documents"]
    assert result["documents"][0]["citation"]["title"] == "工伤保险条例"


def test_payment_calculation_returns_assumptions_and_items():
    result = calculate_payment(
        {
            "province": "四川省",
            "disability_grade": "十级",
            "monthly_wage": 6000,
        }
    )

    assert result["items"][0]["name"] == "一次性伤残补助金"
    assert result["items"][0]["amount"] == 42000
    assert "以当地政策和经办机构核定为准" in result["disclaimer"]


def test_citation_formatter_outputs_ordered_citations():
    citations = format_citations(
        {
            "documents": [
                {"citation": {"title": "工伤保险条例", "article": "第十四条"}},
                {"citation": {"title": "四川省工伤保险条例实施办法", "article": "待遇章节"}},
            ]
        }
    )

    assert citations["citations"][0]["label"] == "[1] 工伤保险条例 第十四条"
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_mvp_tools.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.tools.policy_rag'`。

- [ ] **步骤 3：实现 fixture 与工具函数**

创建 `data/policies/policy_fixtures.jsonl`：

```jsonl
{"id":"policy_001","title":"工伤保险条例","article":"第十四条","province":"全国","city":"","keywords":["上下班途中","交通事故","非本人主要责任","工伤认定"],"content":"在上下班途中，受到非本人主要责任的交通事故伤害的，应当认定为工伤。"}
{"id":"policy_002","title":"劳动能力鉴定办事指南","article":"材料章节","province":"全国","city":"","keywords":["劳动能力鉴定","材料","伤残等级"],"content":"申请劳动能力鉴定通常需要工伤认定决定书、诊断证明、病历材料和身份证明等材料。"}
{"id":"policy_003","title":"四川省工伤保险条例实施办法","article":"待遇章节","province":"四川省","city":"","keywords":["十级","待遇","一次性伤残补助金"],"content":"工伤待遇应结合伤残等级、本人工资、统筹地区政策和经办机构核定结果计算。"}
```

创建 `ananhu_agent/tools/policy_rag.py`：

```python
import json
from pathlib import Path
from typing import Any


def search_policy(payload: dict[str, Any]) -> dict[str, Any]:
    query = payload["query"]
    province = payload.get("province")
    top_k = int(payload.get("top_k", 3))
    fixture_path = Path(payload.get("fixture_path", "data/policies/policy_fixtures.jsonl"))
    rows = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines()]
    scored = []
    for row in rows:
        region_match = row["province"] in ("全国", province, None, "")
        keyword_score = sum(1 for keyword in row["keywords"] if keyword in query)
        if region_match and keyword_score > 0:
            scored.append((keyword_score, row))
    documents = [
        {
            "id": row["id"],
            "content": row["content"],
            "citation": {"title": row["title"], "article": row["article"]},
        }
        for _, row in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
    ]
    return {"documents": documents}
```

创建 `ananhu_agent/tools/payment_calculation.py`：

```python
from typing import Any

GRADE_MONTHS = {"十级": 7, "九级": 9, "八级": 11, "七级": 13}


def calculate_payment(payload: dict[str, Any]) -> dict[str, Any]:
    grade = payload["disability_grade"]
    monthly_wage = int(payload["monthly_wage"])
    months = GRADE_MONTHS[grade]
    amount = monthly_wage * months
    return {
        "items": [
            {
                "name": "一次性伤残补助金",
                "formula": f"{monthly_wage} * {months}",
                "amount": amount,
            }
        ],
        "assumptions": {
            "province": payload.get("province"),
            "disability_grade": grade,
            "monthly_wage": monthly_wage,
        },
        "disclaimer": "测算结果仅供咨询参考，以当地政策和经办机构核定为准。",
    }
```

创建 `ananhu_agent/tools/formatters.py`：

```python
from typing import Any


def format_citations(payload: dict[str, Any]) -> dict[str, Any]:
    citations = []
    for index, document in enumerate(payload["documents"], start=1):
        citation = document["citation"]
        citations.append(
            {
                "index": index,
                "label": f"[{index}] {citation['title']} {citation['article']}",
                "title": citation["title"],
                "article": citation["article"],
            }
        )
    return {"citations": citations}
```

- [ ] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_mvp_tools.py -v
```

预期：3 passed。

- [ ] **步骤 5：提交**

```bash
git add data/policies ananhu_agent/tools/policy_rag.py ananhu_agent/tools/payment_calculation.py ananhu_agent/tools/formatters.py tests/test_mvp_tools.py
git commit -m "feat: add local policy and payment tools"
```

**验收标准：**

- RAG 工具能返回法规依据和 citation。
- 待遇测算返回分项、公式、假设和免责声明。
- 引用格式化输出稳定有序。

### 任务 8：实现确定性模型路由和 IntentRouterAgent

**目标：** 在无真实模型 key 的情况下，先用 deterministic fake model 跑通意图识别和槽位抽取测试。

**涉及模块：** `models`、`agents`。

**前置依赖：** 任务 2、任务 4。

**文件：**
- 创建：`ananhu_agent/models/__init__.py`
- 创建：`ananhu_agent/models/fake_model.py`
- 创建：`ananhu_agent/models/model_router.py`
- 创建：`ananhu_agent/agents/__init__.py`
- 创建：`ananhu_agent/agents/intent_router.py`
- 创建：`tests/test_intent_router_agent.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_intent_router_agent.py`：

```python
from pathlib import Path

from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.models.fake_model import FakeModelClient
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext


def test_intent_router_extracts_payment_intent_and_slots_through_prompt_context():
    agent = IntentRouterAgent(
        FakeModelClient(),
        ContextManager(),
        PromptManager(Path("ananhu_agent/prompts/templates")),
    )
    ctx = AgentContext.new_for_query(
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
    )

    message = agent.run(ctx)

    assert message.data["intent"] == "payment_calculation"
    assert message.data["slots"]["province"] == "四川省"
    assert message.data["slots"]["disability_grade"] == "十级"
    assert message.data["slots"]["monthly_wage"] == 6000
    assert message.data["prompt_ref"] == "intent_router.v1"
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_intent_router_agent.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.agents'`。

- [ ] **步骤 3：实现 fake model 和 agent**

创建 `ananhu_agent/models/__init__.py` 和 `ananhu_agent/agents/__init__.py` 为空文件。

创建 `ananhu_agent/models/fake_model.py`：

```python
import re
from typing import Any


class FakeModelClient:
    def classify_and_extract(self, query: str) -> dict[str, Any]:
        slots: dict[str, Any] = {}
        if "四川" in query:
            slots["province"] = "四川省"
        if "十级" in query:
            slots["disability_grade"] = "十级"
        wage_match = re.search(r"月工资(\d+)", query)
        if wage_match:
            slots["monthly_wage"] = int(wage_match.group(1))
        if "赔多少钱" in query or "待遇" in query:
            intent = "payment_calculation"
        elif "劳动能力鉴定" in query:
            intent = "labor_capacity"
        elif "工伤" in query or "交通事故" in query:
            intent = "work_injury_recognition"
        else:
            intent = "other"
        return {
            "intent": intent,
            "confidence": 0.9,
            "slots": slots,
            "is_composite": False,
            "missing_slots": [],
        }
```

创建 `ananhu_agent/models/model_router.py`：

```python
from ananhu_agent.models.fake_model import FakeModelClient


class ModelRouter:
    def __init__(self) -> None:
        self.fake_client = FakeModelClient()

    def client_for(self, model_profile: str) -> FakeModelClient:
        return self.fake_client
```

创建 `ananhu_agent/agents/intent_router.py`：

```python
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.models.fake_model import FakeModelClient
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext, AgentMessage


class IntentRouterAgent:
    name = "IntentRouterAgent"

    def __init__(
        self,
        model_client: FakeModelClient,
        context_manager: ContextManager,
        prompt_manager: PromptManager,
    ) -> None:
        self.model_client = model_client
        self.context_manager = context_manager
        self.prompt_manager = prompt_manager

    def run(self, ctx: AgentContext) -> AgentMessage:
        sections, context_metadata = self.context_manager.build_sections(ctx)
        rendered = self.prompt_manager.render("intent_router.v1", sections)
        result = self.model_client.classify_and_extract(rendered.text)
        result["prompt_ref"] = rendered.metadata["id"]
        result["prompt_metadata"] = rendered.metadata
        result["context_metadata"] = context_metadata
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content=f"识别为 {result['intent']}",
            data=result,
            tool_calls=[],
            missing_slots=result["missing_slots"],
            citations=[],
            warnings=[],
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_intent_router_agent.py -v
```

预期：1 passed。

- [ ] **步骤 5：提交**

```bash
git add ananhu_agent/models ananhu_agent/agents tests/test_intent_router_agent.py
git commit -m "feat: add deterministic intent router agent"
```

**验收标准：**

- 无真实模型 key 时测试稳定。
- `IntentRouterAgent` 只返回结构化消息，不写上下文。
- 意图识别必须经过 `ContextManager` 和 `PromptManager`，并在 `AgentMessage.data` 中返回 `prompt_ref`、`prompt_metadata` 和 `context_metadata`，供 Orchestrator 写 `prompt_built` / `model_called` trace。

### 任务 9：实现 PolicyRAGAgent、DomainConsultationAgent、PaymentCalculationAgent

**目标：** 3 个业务 Agent 通过 ToolCallRequest 表达意图，由 Orchestrator 或测试显式调用 ToolExecutor。

**涉及模块：** `agents`、`schemas`。

**前置依赖：** 任务 6、任务 7、任务 8。

**文件：**
- 创建：`ananhu_agent/agents/policy_rag.py`
- 创建：`ananhu_agent/agents/domain_consultation.py`
- 创建：`ananhu_agent/agents/payment_calculation.py`
- 创建：`tests/test_business_agents.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_business_agents.py`：

```python
from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.schemas import AgentContext, IntentResult


def test_domain_agent_returns_structured_need_for_policy_evidence():
    ctx = AgentContext.new_for_query("sess_1", 1, "上班路上交通事故算工伤吗？")
    ctx.intent_result = IntentResult(intent="work_injury_recognition", confidence=0.9)

    message = DomainConsultationAgent().run(ctx)

    assert message.agent_name == "DomainConsultationAgent"
    assert message.data["needs_policy_evidence"] is True
    assert message.tool_calls == []


def test_payment_agent_requests_calculation_and_policy_tools():
    ctx = AgentContext.new_for_query("sess_1", 1, "四川十级工伤月工资6000赔多少钱？")
    ctx.intent_result = IntentResult(
        intent="payment_calculation",
        confidence=0.9,
        slots={"province": "四川省", "disability_grade": "十级", "monthly_wage": 6000},
    )

    message = PaymentCalculationAgent().run(ctx)

    assert [call.tool_name for call in message.tool_calls] == ["PaymentCalculationTool"]


def test_policy_rag_agent_requests_policy_rag_tool():
    from ananhu_agent.agents.policy_rag import PolicyRAGAgent

    ctx = AgentContext.new_for_query("sess_1", 1, "劳动能力鉴定需要准备哪些材料？")
    message = PolicyRAGAgent().run(ctx)

    assert message.tool_calls[0].tool_name == "PolicyRAGTool"
    assert message.tool_calls[0].called_by == "PolicyRAGAgent"
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_business_agents.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.agents.domain_consultation'`。

- [ ] **步骤 3：实现业务 Agent**

创建 `ananhu_agent/agents/domain_consultation.py`：

```python
from ananhu_agent.schemas import AgentContext, AgentMessage


class DomainConsultationAgent:
    name = "DomainConsultationAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="需要检索政策依据后回答。",
            data={"needs_policy_evidence": True},
            tool_calls=[],
        )
```

创建 `ananhu_agent/agents/payment_calculation.py`：

```python
from uuid import uuid4

from ananhu_agent.schemas import AgentContext, AgentMessage, ToolCallRequest


class PaymentCalculationAgent:
    name = "PaymentCalculationAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        slots = ctx.intent_result.slots if ctx.intent_result else {}
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="需要测算待遇并补充政策依据。",
            tool_calls=[
                ToolCallRequest(
                    tool_call_id=f"tool_{uuid4().hex[:8]}",
                    tool_name="PaymentCalculationTool",
                    called_by=self.name,
                    input={
                        "province": slots.get("province"),
                        "disability_grade": slots.get("disability_grade"),
                        "monthly_wage": slots.get("monthly_wage"),
                    },
                ),
            ],
        )
```

创建 `ananhu_agent/agents/policy_rag.py`：

```python
from uuid import uuid4

from ananhu_agent.schemas import AgentContext, AgentMessage, ToolCallRequest


class PolicyRAGAgent:
    name = "PolicyRAGAgent"

    def run(self, ctx: AgentContext) -> AgentMessage:
        return AgentMessage(
            agent_name=self.name,
            status="success",
            content="检索政策依据。",
            tool_calls=[
                ToolCallRequest(
                    tool_call_id=f"tool_{uuid4().hex[:8]}",
                    tool_name="PolicyRAGTool",
                    called_by=self.name,
                    input={
                        "query": ctx.request.user_query,
                        "province": ctx.request.province,
                        "city": ctx.request.city,
                        "top_k": 3,
                    },
                )
            ],
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_business_agents.py -v
```

预期：3 passed。

- [ ] **步骤 5：提交**

```bash
git add ananhu_agent/agents/policy_rag.py ananhu_agent/agents/domain_consultation.py ananhu_agent/agents/payment_calculation.py tests/test_business_agents.py
git commit -m "feat: add mvp business agents"
```

**验收标准：**

- 业务 Agent 不直接调用工具函数。
- 工具调用统一表达为 `ToolCallRequest`。
- `PolicyRAGTool` 只由 `PolicyRAGAgent` 请求；Domain / Payment 链路需要政策依据时，由 Orchestrator 串行调用 `PolicyRAGAgent`。

### 任务 10：实现答案聚合、校验和安全守卫

**目标：** 最终回答必须包含结论、依据、适用条件、材料建议或测算假设、风险提示，并拦截绝对化表达。

**涉及模块：** `orchestrator`。

**前置依赖：** 任务 2、任务 7。

**文件：**
- 创建：`ananhu_agent/orchestrator/aggregator.py`
- 创建：`ananhu_agent/orchestrator/validators.py`
- 创建：`ananhu_agent/orchestrator/safety.py`
- 创建：`tests/test_answer_governance.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_answer_governance.py`：

```python
from ananhu_agent.orchestrator.aggregator import build_final_answer
from ananhu_agent.orchestrator.safety import PolicySafetyGuard
from ananhu_agent.orchestrator.validators import AnswerValidator
from ananhu_agent.schemas import AgentContext, ToolCallResult


def test_final_answer_includes_citation_and_risk_note():
    ctx = AgentContext.new_for_query("sess_1", 1, "上班路上交通事故算工伤吗？")
    ctx.tool_results.append(
        ToolCallResult(
            tool_call_id="tool_1",
            tool_name="PolicyRAGTool",
            called_by="DomainConsultationAgent",
            tool_status="success",
            tool_error_code=None,
            latency_ms=1,
            input={},
            output={
                "documents": [
                    {
                        "content": "上下班途中非本人主要责任交通事故应认定为工伤。",
                        "citation": {"title": "工伤保险条例", "article": "第十四条"},
                    }
                ]
            },
            fallback_used=False,
        )
    )

    answer = build_final_answer(ctx)

    assert "工伤保险条例" in answer
    assert "以经办机构和正式材料为准" in answer


def test_validator_rejects_answer_without_citation():
    result = AnswerValidator().validate("这个一定算工伤。", citations=[])

    assert result.passed is False
    assert "missing_citation" in result.issues


def test_safety_guard_rejects_absolute_commitment():
    result = PolicySafetyGuard().check("你这个一定能认定工伤。")

    assert result.passed is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_answer_governance.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.orchestrator.aggregator'`。

- [ ] **步骤 3：实现聚合、校验、安全守卫**

创建 `ananhu_agent/orchestrator/aggregator.py`：

```python
from ananhu_agent.schemas import AgentContext


def build_final_answer(ctx: AgentContext) -> str:
    documents = []
    payment_items = []
    for result in ctx.tool_results:
        if result.tool_name == "PolicyRAGTool":
            documents.extend(result.output.get("documents", []))
        if result.tool_name == "PaymentCalculationTool":
            payment_items.extend(result.output.get("items", []))

    lines = ["结论：需结合事实和材料判断，以下为咨询参考。"]
    if payment_items:
        lines.append("测算：")
        for item in payment_items:
            lines.append(f"- {item['name']}：{item['amount']} 元，公式：{item['formula']}")
    if documents:
        lines.append("依据：")
        for index, doc in enumerate(documents, start=1):
            citation = doc["citation"]
            lines.append(f"[{index}] {citation['title']} {citation['article']}：{doc['content']}")
    lines.append("风险提示：具体结论以经办机构和正式材料为准。")
    return "\n".join(lines)
```

创建 `ananhu_agent/orchestrator/validators.py`：

```python
from ananhu_agent.schemas import VerificationResult


class AnswerValidator:
    def validate(self, answer: str, citations: list[dict]) -> VerificationResult:
        issues = []
        if not citations:
            issues.append("missing_citation")
        return VerificationResult(passed=not issues, issues=issues)
```

创建 `ananhu_agent/orchestrator/safety.py`：

```python
from ananhu_agent.schemas import SafetyResult

ABSOLUTE_PHRASES = ("一定能", "肯定能", "保证", "必然认定")


class PolicySafetyGuard:
    def check(self, answer: str) -> SafetyResult:
        warnings = [phrase for phrase in ABSOLUTE_PHRASES if phrase in answer]
        return SafetyResult(passed=not warnings, warnings=warnings)
```

- [ ] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_answer_governance.py -v
```

预期：3 passed。

- [ ] **步骤 5：提交**

```bash
git add ananhu_agent/orchestrator/aggregator.py ananhu_agent/orchestrator/validators.py ananhu_agent/orchestrator/safety.py tests/test_answer_governance.py
git commit -m "feat: add answer aggregation and safety checks"
```

**验收标准：**

- 最终答案包含依据和风险提示。
- 无结构化 citation 时校验失败，即使自然语言答案包含“依据”二字也不能通过。
- 绝对化承诺被安全守卫拦截。

### 任务 11：实现 AgentOrchestrator 单轮同步主流程

**目标：** 跑通从请求到最终答案的同步垂直链路，并记录关键 trace。

**涉及模块：** `orchestrator`、`agents`、`tools`、`storage`。

**前置依赖：** 任务 4、任务 6、任务 7、任务 8、任务 9、任务 10。

**文件：**
- 创建：`ananhu_agent/orchestrator/orchestrator.py`
- 创建：`tests/test_orchestrator_vertical_slice.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_orchestrator_vertical_slice.py`：

```python
from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator


def test_orchestrator_answers_payment_question_with_trace(tmp_path):
    orchestrator = create_default_orchestrator(tmp_path)

    ctx = orchestrator.ask(
        session_id="sess_1",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
    )

    assert ctx.final_answer is not None
    assert "一次性伤残补助金" in ctx.final_answer
    assert "42000" in ctx.final_answer
    assert "以经办机构和正式材料为准" in ctx.final_answer
    events = orchestrator.trace_recorder.read_all()
    event_types = [event["event_type"] for event in events]
    assert event_types[0] == "request_received"
    assert "intent_recognized" in event_types
    assert "intent_revised" in event_types
    assert "slots_merged" in event_types
    assert "prompt_built" in event_types
    assert "model_called" in event_types
    assert "tool_finished" in event_types
    assert "answer_validated" in event_types
    assert "safety_checked" in event_types
    assert "response_ready" in event_types
    assert orchestrator.task_state_store.read_all()[0]["current_phase"] == "response_ready"
    assert orchestrator.report_store.read_all()[0]["final_intent"] == "payment_calculation"
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_orchestrator_vertical_slice.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.orchestrator.orchestrator'`。

- [ ] **步骤 3：实现 Orchestrator 和默认装配**

创建 `ananhu_agent/orchestrator/orchestrator.py`：

```python
from pathlib import Path

from ananhu_agent.agents.domain_consultation import DomainConsultationAgent
from ananhu_agent.agents.intent_router import IntentRouterAgent
from ananhu_agent.agents.payment_calculation import PaymentCalculationAgent
from ananhu_agent.agents.policy_rag import PolicyRAGAgent
from ananhu_agent.context.context_manager import ContextManager
from ananhu_agent.context.slot_rules import merge_slots
from ananhu_agent.models.fake_model import FakeModelClient
from ananhu_agent.orchestrator.aggregator import build_final_answer
from ananhu_agent.orchestrator.rules import revise_intent
from ananhu_agent.orchestrator.safety import PolicySafetyGuard
from ananhu_agent.orchestrator.validators import AnswerValidator
from ananhu_agent.prompts.prompt_manager import PromptManager
from ananhu_agent.schemas import AgentContext, AgentPlan, IntentResult, RunReport, TaskState, TraceEvent
from ananhu_agent.storage.runtime_stores import ReportStore, TaskStateStore, TraceRecorder
from ananhu_agent.tools.executor import ToolExecutor
from ananhu_agent.tools.payment_calculation import calculate_payment
from ananhu_agent.tools.policy_rag import search_policy
from ananhu_agent.tools.registry import ToolDefinition, ToolRegistry


class AgentOrchestrator:
    def __init__(
        self,
        intent_agent: IntentRouterAgent,
        domain_agent: DomainConsultationAgent,
        payment_agent: PaymentCalculationAgent,
        policy_rag_agent: PolicyRAGAgent,
        tool_executor: ToolExecutor,
        trace_recorder: TraceRecorder,
        task_state_store: TaskStateStore,
        report_store: ReportStore,
    ) -> None:
        self.intent_agent = intent_agent
        self.domain_agent = domain_agent
        self.payment_agent = payment_agent
        self.policy_rag_agent = policy_rag_agent
        self.tool_executor = tool_executor
        self.trace_recorder = trace_recorder
        self.task_state_store = task_state_store
        self.report_store = report_store

    def ask(self, session_id: str, turn_id: int, user_query: str) -> AgentContext:
        ctx = AgentContext.new_for_query(session_id, turn_id, user_query)
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "request_received",
                "orchestrator",
                {"user_query": user_query},
            )
        )
        intent_message = self.intent_agent.run(ctx)
        ctx.agent_outputs.append(intent_message)
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "prompt_built",
                "prompt",
                {
                    "prompt_ref": intent_message.data["prompt_ref"],
                    "prompt_metadata": intent_message.data["prompt_metadata"],
                    "context_metadata": intent_message.data["context_metadata"],
                },
            )
        )
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "model_called",
                "model",
                {"model_profile": "intent_fast", "prompt_ref": intent_message.data["prompt_ref"]},
            )
        )
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "intent_recognized",
                "routing",
                intent_message.data,
            )
        )
        ctx.intent_result = revise_intent(user_query, IntentResult(**intent_message.data))
        active_slots, slot_metadata = merge_slots(ctx.conversation.active_slots, ctx.intent_result.slots)
        ctx.conversation.active_slots = active_slots
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "intent_revised",
                "routing",
                ctx.intent_result.model_dump(),
            )
        )
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "slots_merged",
                "routing",
                {"active_slots": active_slots, "metadata": slot_metadata},
            )
        )
        if ctx.intent_result.intent == "payment_calculation":
            ctx.agent_plan = AgentPlan(
                route_agents=["PaymentCalculationAgent", "PolicyRAGAgent"],
                required_tools=["PaymentCalculationTool", "PolicyRAGTool"],
            )
            message = self.payment_agent.run(ctx)
        else:
            ctx.agent_plan = AgentPlan(
                route_agents=["DomainConsultationAgent", "PolicyRAGAgent"],
                required_tools=["PolicyRAGTool"],
            )
            message = self.domain_agent.run(ctx)
        ctx.agent_outputs.append(message)
        for call in message.tool_calls:
            ctx.tool_results.append(
                self.tool_executor.execute(
                    ctx.request.request_id,
                    ctx.request.session_id,
                    call,
                )
            )
        policy_message = self.policy_rag_agent.run(ctx)
        ctx.agent_outputs.append(policy_message)
        for call in policy_message.tool_calls:
            ctx.tool_results.append(
                self.tool_executor.execute(
                    ctx.request.request_id,
                    ctx.request.session_id,
                    call,
                )
            )
        ctx.final_answer = build_final_answer(ctx)
        citations = [
            document["citation"]
            for result in ctx.tool_results
            if result.tool_name == "PolicyRAGTool"
            for document in result.output.get("documents", [])
        ]
        ctx.verification_result = AnswerValidator().validate(ctx.final_answer, citations)
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "answer_validated",
                "validation",
                ctx.verification_result.model_dump(),
            )
        )
        ctx.safety_result = PolicySafetyGuard().check(ctx.final_answer)
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "safety_checked",
                "safety",
                ctx.safety_result.model_dump(),
            )
        )
        self.trace_recorder.record(
            TraceEvent.new(
                ctx.request.request_id,
                ctx.request.session_id,
                "response_ready",
                "orchestrator",
                {"final_answer": ctx.final_answer},
            )
        )
        self.task_state_store.append(
            TaskState(
                id=f"state_{ctx.request.request_id}",
                session_id=ctx.request.session_id,
                turn_id=ctx.request.turn_id,
                user_query=user_query,
                status="completed",
                current_phase="response_ready",
                raw_intent=intent_message.data["intent"],
                revised_intent=ctx.intent_result.intent,
                active_slots=ctx.conversation.active_slots,
                missing_slots=ctx.intent_result.missing_slots,
                route_agents=ctx.agent_plan.route_agents,
                prompt_refs=[intent_message.data["prompt_ref"]],
                tool_steps=[result.tool_name for result in ctx.tool_results],
                model_attempts=1,
                fallback_used=any(result.fallback_used for result in ctx.tool_results),
                error_message=None,
            )
        )
        self.report_store.append(
            RunReport(
                id=f"report_{ctx.request.request_id}",
                session_id=ctx.request.session_id,
                final_status="success",
                final_intent=ctx.intent_result.intent,
                route_agents=ctx.agent_plan.route_agents,
                tool_count=len(ctx.tool_results),
                model_attempts=1,
                prompt_refs=[intent_message.data["prompt_ref"]],
                prompt_metadata={intent_message.data["prompt_ref"]: intent_message.data["prompt_metadata"]},
                output_schema_valid_rate=1.0 if ctx.verification_result.passed else 0.0,
                token_usage={},
                latency_ms=0,
                fallback_used=any(result.fallback_used for result in ctx.tool_results),
                safety_result=ctx.safety_result.model_dump(),
                badcase_candidate=not ctx.verification_result.passed or not ctx.safety_result.passed,
            )
        )
        return ctx


def create_default_orchestrator(base_path: Path) -> AgentOrchestrator:
    trace_recorder = TraceRecorder(base_path / "traces.jsonl")
    task_state_store = TaskStateStore(base_path / "task_states.jsonl")
    report_store = ReportStore(base_path / "run_reports.jsonl")
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="PolicyRAGTool",
            description="检索工伤法规、地方政策、办事指南",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query"],
            handler=search_policy,
        )
    )
    registry.register(
        ToolDefinition(
            name="PaymentCalculationTool",
            description="工伤待遇测算",
            risk_level="calculation",
            timeout_ms=3000,
            allowed_callers=["PaymentCalculationAgent"],
            required_input_keys=["disability_grade", "monthly_wage"],
            handler=calculate_payment,
        )
    )
    return AgentOrchestrator(
        intent_agent=IntentRouterAgent(
            FakeModelClient(),
            ContextManager(),
            PromptManager(Path("ananhu_agent/prompts/templates")),
        ),
        domain_agent=DomainConsultationAgent(),
        payment_agent=PaymentCalculationAgent(),
        policy_rag_agent=PolicyRAGAgent(),
        tool_executor=ToolExecutor(registry, trace_recorder),
        trace_recorder=trace_recorder,
        task_state_store=task_state_store,
        report_store=report_store,
    )
```

- [ ] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_orchestrator_vertical_slice.py -v
```

预期：1 passed。

- [ ] **步骤 5：提交**

```bash
git add ananhu_agent/orchestrator/orchestrator.py tests/test_orchestrator_vertical_slice.py
git commit -m "feat: add orchestrator vertical slice"
```

**验收标准：**

- Orchestrator 是唯一合并上下文并推进状态的组件。
- Payment 链路必须先由 `PaymentCalculationAgent` 触发测算，再由 `PolicyRAGAgent` 触发 RAG；两者都必须经过 ToolExecutor。
- trace 至少包含 `request_received`、`intent_recognized`、`intent_revised`、`slots_merged`、`prompt_built`、`model_called`、`tool_finished`、`answer_validated`、`safety_checked`、`response_ready`。
- `task_states.jsonl` 和 `run_reports.jsonl` 必须各有一条本轮运行证据。

### 任务 12：实现 CLI ask 与交互式入口

**目标：** 用户能通过 CLI 单轮提问，看到最终答案和 trace 文件位置。

**涉及模块：** `cli`。

**前置依赖：** 任务 11。

**文件：**
- 修改：`ananhu_agent/cli/main.py`
- 创建：`tests/test_cli_ask.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_cli_ask.py`：

```python
from typer.testing import CliRunner

from ananhu_agent.cli.main import app


def test_cli_ask_outputs_final_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["ask", "四川十级工伤，月工资6000，大概能赔多少钱？"],
    )

    assert result.exit_code == 0
    assert "一次性伤残补助金" in result.output
    assert "Trace:" in result.output
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_cli_ask.py -v
```

预期：FAIL，报错包含 `No such command 'ask'`。

- [ ] **步骤 3：实现 ask 命令**

修改 `ananhu_agent/cli/main.py`：

```python
from pathlib import Path
import os

import typer

from ananhu_agent import __version__
from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator

app = typer.Typer(help="安安虎工伤智能助手 CLI MVP")


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(f"ananhu-agent {__version__}")


@app.command()
def ask(query: str) -> None:
    """Ask one work injury consultation question."""
    runtime_dir = Path(os.getenv("ANANHU_RUNTIME_DIR", ".ananhu-runtime"))
    orchestrator = create_default_orchestrator(runtime_dir)
    ctx = orchestrator.ask(session_id="cli", turn_id=1, user_query=query)
    typer.echo(ctx.final_answer)
    typer.echo(f"Trace: {runtime_dir / 'traces.jsonl'}")
```

- [ ] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_cli_ask.py -v
```

预期：1 passed。

- [ ] **步骤 5：提交**

```bash
git add ananhu_agent/cli/main.py tests/test_cli_ask.py
git commit -m "feat: add cli ask command"
```

**验收标准：**

- `uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"` 输出测算结果。
- 输出包含 trace 文件路径。

### 任务 13：实现 eval runner、metrics 和 badcase 记录

**目标：** CLI 能运行固定评测集，产出 metrics，并将失败案例写入 badcase JSONL。

**涉及模块：** `evaluation`、`cli`、`storage`。

**前置依赖：** 任务 11、任务 12。

**文件：**
- 创建：`data/eval/eval_cases.jsonl`
- 创建：`ananhu_agent/evaluation/__init__.py`
- 创建：`ananhu_agent/evaluation/metrics.py`
- 创建：`ananhu_agent/evaluation/runner.py`
- 修改：`ananhu_agent/cli/main.py`
- 创建：`tests/test_eval_runner.py`
- 创建：`tests/test_cli_eval.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_eval_runner.py`：

```python
from pathlib import Path

from ananhu_agent.evaluation.runner import EvalRunner
from ananhu_agent.orchestrator.orchestrator import create_default_orchestrator


def test_eval_runner_outputs_metrics_and_badcases(tmp_path):
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","expect_contains":["一次性伤残补助金","42000"]}\n'
        '{"id":"case_2","query":"劳动能力鉴定需要准备哪些材料？","expect_contains":["这个片段不会出现，用来验证 badcase 写入"]}\n',
        encoding="utf-8",
    )
    runner = EvalRunner(create_default_orchestrator(tmp_path), tmp_path)

    metrics = runner.run(cases)

    assert metrics["total"] == 2
    assert metrics["passed"] == 1
    assert metrics["failed"] == 1
    assert (tmp_path / "metrics.json").exists()
    badcases = (tmp_path / "badcases.jsonl").read_text(encoding="utf-8")
    assert "case_2" in badcases
    assert "eval_failed" in badcases
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_eval_runner.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.evaluation'`。

- [ ] **步骤 3：实现 eval runner 与 metrics**

创建 `data/eval/eval_cases.jsonl`：

```jsonl
{"id":"eval_payment_001","query":"四川十级工伤，月工资6000，大概能赔多少钱？","expect_contains":["一次性伤残补助金","42000","以经办机构和正式材料为准"]}
{"id":"eval_recognition_001","query":"上班路上发生交通事故，交警认定我不是主要责任，能不能认定工伤？","expect_contains":["工伤保险条例","以经办机构和正式材料为准"]}
{"id":"eval_labor_001","query":"劳动能力鉴定需要准备哪些材料？","expect_contains":["劳动能力鉴定"]}
```

创建 `ananhu_agent/evaluation/__init__.py`：

```python
```

创建 `ananhu_agent/evaluation/metrics.py`：

```python
def score_case(answer: str, expected: list[str]) -> bool:
    return all(fragment in answer for fragment in expected)
```

创建 `ananhu_agent/evaluation/runner.py`：

```python
import json
from pathlib import Path
from typing import Any

from ananhu_agent.evaluation.metrics import score_case
from ananhu_agent.orchestrator.orchestrator import AgentOrchestrator
from ananhu_agent.storage.jsonl_store import JsonlStore


class EvalRunner:
    def __init__(self, orchestrator: AgentOrchestrator, output_dir: Path) -> None:
        self.orchestrator = orchestrator
        self.output_dir = output_dir

    def run(self, cases_path: Path) -> dict[str, Any]:
        rows = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines()]
        badcases = JsonlStore(self.output_dir / "badcases.jsonl")
        passed = 0
        for index, case in enumerate(rows, start=1):
            ctx = self.orchestrator.ask("eval", index, case["query"])
            ok = score_case(ctx.final_answer or "", case["expect_contains"])
            if ok:
                passed += 1
            else:
                badcases.append(
                    {
                        "case_id": case["id"],
                        "query": case["query"],
                        "answer": ctx.final_answer,
                        "issue_type": "eval_failed",
                        "expected_answer": case["expect_contains"],
                    }
                )
        metrics = {"total": len(rows), "passed": passed, "failed": len(rows) - passed}
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return metrics
```

- [ ] **步骤 4：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_eval_runner.py -v
```

预期：1 passed。

- [ ] **步骤 5：给 CLI 增加 eval 命令并测试**

修改 `ananhu_agent/cli/main.py`，新增：

```python
@app.command()
def eval(cases: Path = Path("data/eval/eval_cases.jsonl")) -> None:
    """Run local eval cases."""
    runtime_dir = Path(os.getenv("ANANHU_RUNTIME_DIR", ".ananhu-runtime"))
    orchestrator = create_default_orchestrator(runtime_dir)
    from ananhu_agent.evaluation.runner import EvalRunner

    metrics = EvalRunner(orchestrator, runtime_dir).run(cases)
    typer.echo(metrics)
    typer.echo(f"Metrics: {runtime_dir / 'metrics.json'}")
```

创建 `tests/test_cli_eval.py`：

```python
from typer.testing import CliRunner

from ananhu_agent.cli.main import app


def test_cli_eval_outputs_metrics_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANHU_RUNTIME_DIR", str(tmp_path))
    cases = tmp_path / "eval_cases.jsonl"
    cases.write_text(
        '{"id":"case_1","query":"四川十级工伤，月工资6000，大概能赔多少钱？","expect_contains":["一次性伤残补助金"]}\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["eval", str(cases)])

    assert result.exit_code == 0
    assert "Metrics:" in result.output
    assert (tmp_path / "metrics.json").exists()
```

运行：

```bash
uv run pytest tests/test_eval_runner.py tests/test_cli_ask.py tests/test_cli_eval.py -v
```

预期：3 passed。

- [ ] **步骤 6：提交**

```bash
git add data/eval ananhu_agent/evaluation ananhu_agent/cli/main.py tests/test_eval_runner.py tests/test_cli_eval.py
git commit -m "feat: add eval runner and badcase output"
```

**验收标准：**

- eval 输出 `total`、`passed`、`failed`。
- 失败样例写入 `badcases.jsonl`。
- metrics 写入 `metrics.json`。
- CLI `eval` 命令通过 `CliRunner` 验证，输出 metrics 路径。

### 任务 14：补全文档命令和架构变更记录

**目标：** 实现完成后，文档事实与代码入口保持一致。

**涉及模块：** 文档。

**前置依赖：** 任务 1 至任务 13。

**文件：**
- 修改：`docs/backend-conventions.md`
- 修改：`docs/architecture/99-changelog.md`

- [ ] **步骤 1：查看当前文档**

运行：

```bash
sed -n '1,220p' docs/backend-conventions.md
sed -n '1,220p' docs/architecture/99-changelog.md
```

预期：能看到当前文档顶部仍是架构基线阶段的旧状态描述，且 changelog 没有 CLI MVP 实现记录。

- [ ] **步骤 2：更新项目状态和后端命令**

在 `docs/backend-conventions.md` 中先把顶部项目状态段改为：

```markdown
当前项目已初始化 Python CLI MVP 代码结构，本规范用于约束后续 Agent、Tool、Prompt、Trace、Eval 等模块演进。
```

然后在 `docs/backend-conventions.md` 的“本地命令”或“测试与验证”位置补充：

```markdown
## 本地命令

安装开发依赖：

```bash
uv sync --extra dev
```

运行单轮 CLI：

```bash
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
```

运行评测：

```bash
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```

运行测试：

```bash
uv run pytest -v
```
```

- [ ] **步骤 3：更新 changelog**

在 `docs/architecture/99-changelog.md` 追加：

```markdown
## 2026-07-09

- 初始化 Python CLI MVP 工程结构。
- 落地 `AgentContext`、`AgentMessage`、`ToolCallResult`、`TraceEvent` 等运行时协议。
- 增加本地 JSONL trace、metrics、badcase 输出。
- 增加 `AgentOrchestrator` 单轮同步链路和 CLI `ask` / `eval` 命令。
- MVP 工具先使用本地 fixture RAG 和确定性待遇测算，后续可在不改变 ToolExecutor 契约的前提下替换为真实 RAG / 模型。
```

- [ ] **步骤 4：运行全量验证**

运行：

```bash
uv run pytest -v
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```

预期：

- pytest 全部通过。
- ask 输出包含 `一次性伤残补助金`、`42000`、`以经办机构和正式材料为准`。
- eval 输出 metrics 路径。

- [ ] **步骤 5：提交**

```bash
git add docs/backend-conventions.md docs/architecture/99-changelog.md
git commit -m "docs: document cli mvp commands"
```

**验收标准：**

- 文档顶部项目状态已更新为“已初始化 Python CLI MVP 代码结构”。
- 本地安装、测试、ask、eval 命令明确。
- 架构 changelog 记录实现事实变更。

## 4. 对抗性审查清单

执行本计划前，必须使用子 agent 或 reviewer 按以下问题审查：

1. 是否存在后置依赖前置使用：后面的类型、函数、命令是否都在前面任务定义过。
2. 是否存在 Agent 绕过 Orchestrator 写状态。
3. 是否存在 Agent 绕过 ToolExecutor 直接调用工具。
4. 是否存在 Agent 硬编码完整 Prompt。
5. 是否存在只建目录、不可验证的任务。
6. 是否存在任务粒度过大，无法在一次小提交中完成。
7. 是否遗漏 P0：工伤认定、劳动能力鉴定、待遇测算、trace、badcase、eval。
8. 是否误加非目标：HTTP API、WebSocket、前端、语音、图片、MCP。

审查通过条件：

- 每个任务都有明确目标、涉及模块、步骤流程、验收标准。
- 每个任务的验证命令能在该任务完成后独立运行。
- 依赖图无循环，无“前面依赖后面”的情况。
- P0 垂直闭环可通过 `uv run ananhu-agent ask` 和 `uv run ananhu-agent eval` 观察。

## 5. 总体验收

最终交付必须满足：

- `uv run pytest -v` 全部通过。
- `uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"` 输出待遇测算、依据和风险提示。
- `uv run ananhu-agent ask "上班路上发生交通事故，交警认定我不是主要责任，能不能认定工伤？"` 输出法规依据和保守结论。
- `uv run ananhu-agent ask "劳动能力鉴定需要准备哪些材料？"` 输出材料建议和依据。
- `.ananhu-runtime/traces.jsonl` 包含 `request_received`、`intent_revised`、`tool_finished`、`response_ready`。
- `uv run ananhu-agent eval data/eval/eval_cases.jsonl` 产出 `.ananhu-runtime/metrics.json`。
- eval 失败时 `.ananhu-runtime/badcases.jsonl` 有结构化记录。
- 没有新增 HTTP API、WebSocket、前端、语音、图片、MCP 能力。

## 6. 执行方式

计划已设计为小任务连续提交。推荐执行方式：

1. **子代理驱动（推荐）**：使用 `superpowers:subagent-driven-development`，每个任务一个新子代理，任务完成后做规格审查和代码质量审查。
2. **内联执行**：使用 `superpowers:executing-plans`，按任务顺序执行，每完成 2 到 3 个任务设置一次检查点。
