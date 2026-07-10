# Textual Chat TUI 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 用单栏 Textual TUI 直接替换 `ananhu-agent chat`，实时展示框架中立节点/模型/工具事件、可折叠输入输出、provider 显式 reasoning、`other` 兜底和本轮聚合 Usage。

**架构：** 先发布 v0.7 架构，再建立唯一的 `RunProgressEvent` 协议和组合 sink。共享 Runtime 阶段包装器、ObservableModelGateway 与 CapabilityGateway 发布事件；Textual 只消费 queue sink，不读取 LangGraph 类型。reasoning 仅存在于序列化排除的瞬态 payload，durable trace 使用显式安全投影。

**技术栈：** Python 3.11、Pydantic v2、Textual、Rich、Typer、LangGraph、pytest、Textual Pilot、uv。

**基线与前置：** 基于 `docs/superpowers/specs/2026-07-10-textual-chat-tui-design.md`；开始本计划前，先完成并合并 OpenAI-compatible JSON Schema 指令、规范槽位名和省级行政区归一化修复。

---

## 文件结构

### 架构与计划

- 创建：`docs/architecture/versions/v0.7-textual-chat-tui.md`，完整架构快照。
- 修改：`TECH_ARCHITECTURE_MVP.md`、`docs/architecture.md`，切换当前版本入口。
- 修改：`docs/architecture/02-agent-runtime.md`，实时事件、取消与终止屏障。
- 修改：`docs/architecture/03-prompt-context.md`，reasoning 瞬态与槽位展示边界。
- 修改：`docs/architecture/04-tools-models.md`，ObservableModelGateway、Usage reported。
- 修改：`docs/architecture/05-data-observability.md`，durable/transient 投影和脱敏。
- 修改：`docs/architecture/99-changelog.md`，记录 v0.7。

### 协议与基础设施

- 创建：`ananhu_agent/ports/run_event_sink.py`，`RunProgressEvent` 判别联合、sink 端口与 no-op。
- 创建：`ananhu_agent/infrastructure/events/run_event_sinks.py`，sequence 分配、trace/queue/组合 sink。
- 修改：`ananhu_agent/schemas.py`，TraceEvent 安全投影需要的兼容字段（如实际需要）。
- 修改：`ananhu_agent/workflow/contracts.py`，cancelled/user-cancelled。
- 修改：`ananhu_agent/capabilities/contracts.py`，CapabilityRequest 增加 run ID。
- 修改：`ananhu_agent/runtime.py`，统一组合根注入 sink、ObservableModelGateway 和 TUI queue。

### Runtime、模型与流程

- 修改：`ananhu_agent/runtimes/native/runtime.py`，共享 stage 生命周期、取消和 run 终止事件。
- 修改：`ananhu_agent/runtimes/langgraph/runtime.py`，复用共享 stage 包装器与终止协议。
- 修改：`ananhu_agent/runtimes/native/stages.py`，删除重复模型埋点并支持 other 无工具路径。
- 创建：`ananhu_agent/models/observable_gateway.py`，统一模型生命周期、瞬态 reasoning 和 usage 事件。
- 修改：`ananhu_agent/ports/model_gateway.py`，reasoning 字段和 Usage reported。
- 修改：`ananhu_agent/infrastructure/models/openai_compatible.py`，解析 reasoning 与 usage reported。
- 修改：`ananhu_agent/infrastructure/models/fake.py`，fake usage 语义。
- 修改：`ananhu_agent/capabilities/tool_executor_gateway.py`、`ananhu_agent/tools/executor.py`，工具运行身份与实时事件。

### TUI

- 创建：`ananhu_agent/cli/tui/app.py`，Textual App、worker、会话和快捷键。
- 创建：`ananhu_agent/cli/tui/widgets/turn.py`，单轮消息与 Usage。
- 创建：`ananhu_agent/cli/tui/widgets/run_inspector.py`，可折叠节点/模型/工具树。
- 创建：`ananhu_agent/cli/tui/presentation.py`，裁剪、脱敏、JSON/Usage 展示模型。
- 创建：`ananhu_agent/cli/tui/modals.py`，帮助、上下文、trace、feedback/badcase。
- 创建：`ananhu_agent/cli/tui/styles.tcss`，单栏、80 列和状态样式。
- 修改：`ananhu_agent/cli/main.py`，`chat` 启动 TUI；ask/eval/version 不导入交互环境。
- 修改：`pyproject.toml`、`uv.lock`，增加 Textual、pytest-asyncio，并打包 TCSS。

### 测试

- 创建：`tests/test_run_progress_events.py`。
- 创建：`tests/runtime_contracts/test_run_progress_contract.py`。
- 创建：`tests/test_model_reasoning_contract.py`。
- 创建：`tests/test_other_intent_flow.py`。
- 创建：`tests/test_tui_presentation.py`。
- 创建：`tests/test_tui_app.py`。
- 创建：`tests/test_tui_terminal.py`。
- 创建：`tests/test_tui_security.py`。
- 修改：`tests/test_cli_chat.py`、`tests/test_cli_feedback_badcase.py`，迁移旧 chat 行为。
- 修改：模型、Capability、Runtime、差分和 CLI 相关现有测试。

## 任务 1：发布 v0.7 架构并锁定依赖

**文件：** 上述架构文档、`pyproject.toml`、`uv.lock`

- [ ] **步骤 1：基于 v0.6 创建完整 v0.7 快照**

复制 `docs/architecture/versions/v0.6-model-catalog.md` 为
`docs/architecture/versions/v0.7-textual-chat-tui.md`，将版本信息改为：

```markdown
| 状态 | 当前有效架构 |
| 版本 | v0.7 |
| 发布日期 | 2026-07-10 |
| 基线版本 | v0.6-model-catalog |
| 变更原因 | 引入框架中立实时运行事件和 Textual Chat TUI，展示节点、模型、工具、reasoning 与 usage。 |
```

正文必须包含：单栏 TUI、RunProgressEvent、public/transient 投影、sequence/gap、取消屏障、reasoning
非持久化、Usage reported、other 无工具路径、旧 chat 能力迁移、兼容策略和限制。

- [ ] **步骤 2：同步架构入口与分册**

更新入口为 v0.7；在 02/03/04/05 和 changelog 中分别维护所有权。不得修改 v0.6 正文。

- [ ] **步骤 3：增加 Textual 依赖**

运行：

```bash
uv add "textual>=1.0"
uv add --optional dev "pytest-asyncio>=0.24"
uv sync --extra dev
```

在 `pyproject.toml` 同步增加：

```toml
[tool.setuptools.package-data]
ananhu_agent = ["prompts/templates/*.yaml", "cli/tui/*.tcss"]
```

预期：Textual 和 pytest-asyncio 已锁定，TCSS 被 wheel 包含；不直接新增 Rich 依赖。

- [ ] **步骤 4：验证架构与依赖**

```bash
uv run python -c "import textual; print(textual.__version__)"
git diff --check
rg -n "v0.7|RunProgressEvent|reasoning_content|Textual" \
  TECH_ARCHITECTURE_MVP.md docs/architecture.md docs/architecture/{02-agent-runtime,03-prompt-context,04-tools-models,05-data-observability,99-changelog}.md
```

预期：命令退出 0；入口只指向 v0.7；v0.6 文件无 diff。

- [ ] **步骤 5：Commit**

```bash
git add pyproject.toml uv.lock TECH_ARCHITECTURE_MVP.md docs/architecture.md docs/architecture/02-agent-runtime.md docs/architecture/03-prompt-context.md docs/architecture/04-tools-models.md docs/architecture/05-data-observability.md docs/architecture/99-changelog.md docs/architecture/versions/v0.7-textual-chat-tui.md
git commit -m "docs(architecture): 发布 Textual Chat TUI 架构 v0.7"
```

## 任务 2：RunProgressEvent、sequence 与安全投影

**文件：** `ananhu_agent/ports/run_event_sink.py`、`ananhu_agent/infrastructure/events/run_event_sinks.py`、`tests/test_run_progress_events.py`、`tests/test_storage.py`

- [ ] **步骤 1：编写事件协议失败测试**

| ID | 函数 |
|---|---|
| EVT-001 | `test_composite_sink_assigns_monotonic_sequence_and_projects_trace` |
| EVT-002 | `test_transient_payload_never_enters_trace_projection` |
| EVT-003 | `test_consumer_rejects_sequence_gap_without_permanent_spinner` |
| EVT-004 | `test_duplicate_and_interleaved_runs_are_isolated` |

```python
def test_composite_sink_assigns_monotonic_sequence_and_projects_trace():
    queue = asyncio.Queue()
    recorder = InMemoryTraceRecorder()
    sink = CompositeRunEventSink(TraceRecorderRunEventSink(recorder), QueueRunEventSink(queue))

    sink.publish(run_event("node_started", run_id="run_1"))
    sink.publish(run_event("node_finished", run_id="run_1"))

    first, second = queue.get_nowait(), queue.get_nowait()
    assert [first.sequence_no, second.sequence_no] == [1, 2]
    assert [row["event_type"] for row in recorder.read_all()] == ["node_started", "node_finished"]


def test_transient_payload_never_enters_trace_projection():
    event = run_event(
        "model_finished",
        public_payload={"reasoning_available": True, "reasoning_length": 18},
        transient_payload={"reasoning_content": "CANARY_REASONING"},
    )
    assert "CANARY_REASONING" not in event.model_dump_json()
    assert "CANARY_REASONING" not in event.to_trace_event().model_dump_json()


def test_consumer_rejects_sequence_gap_without_permanent_spinner():
    inspector = RunEventReducer()
    inspector.apply(numbered_event(1, "node_started"))
    inspector.apply(numbered_event(3, "node_finished"))
    inspector.apply(numbered_event(2, "model_finished"))
    inspector.apply(numbered_event(4, "run_finished"))
    state = inspector.state_for("run_1")
    assert state.error_code == "event_sequence_gap"
    assert state.running is False
    assert state.applied_sequences == [1]
    assert state.terminal_barrier_seen is True


def test_duplicate_and_interleaved_runs_are_isolated():
    inspector = RunEventReducer()
    for event in [event_for("run_a", 1), event_for("run_b", 1), event_for("run_a", 1), event_for("run_a", 2)]:
        inspector.apply(event)
    assert inspector.state_for("run_a").applied_sequences == [1, 2]
    assert inspector.state_for("run_b").applied_sequences == [1]
```

- [ ] **步骤 2：运行测试确认失败**

```bash
uv run pytest tests/test_run_progress_events.py -v
```

预期：FAIL，缺少 `RunProgressEvent`、sink 和 reducer。

- [ ] **步骤 3：实现协议和最小 sink**

在 `run_event_sink.py` 定义公共基类、每类具体事件和真正按 `kind` 判别的联合：

```python
class RunEventBase(BaseModel):
    run_id: str
    request_id: str
    session_id: str
    node_id: str | None = None
    logical_call_id: str | None = None
    attempt: int = 1
    sequence_no: int | None = None
    transient_payload: RunTransientPayload | None = Field(default=None, exclude=True, repr=False)
    created_at: str = Field(default_factory=now_cn)

    def to_trace_event(self) -> TraceEvent:
        return TraceEvent.new(
            run_id=self.run_id,
            request_id=self.request_id,
            session_id=self.session_id,
            event_type=self.kind,
            phase=self.node_id or "run",
            node_id=self.node_id,
            logical_call_id=self.logical_call_id,
            attempt=self.attempt,
            payload={"sequence_no": self.sequence_no, **self.public_payload.model_dump()},
        )

class NodeStartedEvent(RunEventBase):
    kind: Literal["node_started"] = "node_started"
    public_payload: NodeStartedPayload

class ModelFinishedEvent(RunEventBase):
    kind: Literal["model_finished"] = "model_finished"
    public_payload: ModelFinishedPayload

RunProgressEvent = Annotated[
    RunStartedEvent | NodeStartedEvent | NodeFinishedEvent | NodeFailedEvent |
    ModelStartedEvent | ModelFinishedEvent | ModelFailedEvent |
    CapabilityStartedEvent | CapabilityFinishedEvent | CapabilityFailedEvent |
    RunCancelledEvent | RunFinishedEvent,
    Field(discriminator="kind"),
]
```

其余具体事件逐一声明自己的 `Literal[kind]` 和 payload 类型，不使用外层 kind + 任意 payload。sink
入口使用 `TypeAdapter(RunProgressEvent)` 校验；组合 sink 在锁内编号后先 trace、再 queue。

- [ ] **步骤 4：实现纯展示事件 reducer**

`RunEventReducer` 放入 `ananhu_agent/cli/tui/presentation.py` 的无 Textual 纯 Python 区域，完成 duplicate、gap、终止屏障和跨 run 隔离；gap 立即停止 spinner，后续只接受 run_finished 清理确认。

- [ ] **步骤 5：运行事件与存储测试**

```bash
uv run pytest tests/test_run_progress_events.py tests/test_storage.py -v
```

预期：本任务列出的 4 个 EVT 测试全部 PASS；transient canary 在序列化结果中零命中。

- [ ] **步骤 6：Commit**

```bash
git add ananhu_agent/ports/run_event_sink.py ananhu_agent/infrastructure/events/run_event_sinks.py ananhu_agent/cli/tui/presentation.py tests/test_run_progress_events.py tests/test_storage.py
git commit -m "feat(runtime): 增加实时运行事件与安全投影"
```

## 任务 3：Runtime/Capability 生命周期、身份与取消

**文件：** workflow/capability contracts、两种 Runtime、ToolExecutor gateway、runtime contract tests

- [ ] **步骤 1：扩展协议失败测试**

| ID | 函数 |
|---|---|
| EVT-010 | `test_each_node_has_one_terminal_event_and_run_finished_is_last` |
| EVT-011 | `test_cancelled_run_has_one_cancel_and_one_terminal_barrier` |
| EVT-012 | `test_capability_events_keep_full_run_identity` |
| EVT-013 | `test_event_payloads_never_contain_framework_or_ui_types` |
| EVT-014 | `test_native_and_langgraph_emit_equivalent_progress_events` |

在 `tests/runtime_contracts/test_run_progress_contract.py` 参数化 Native/LangGraph：

```python
@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_each_node_has_one_terminal_event_and_run_finished_is_last(runtime_name):
    events = run_with_events(runtime_name, payment_request())
    for started in [e for e in events if e.kind == "node_started"]:
        terminals = [e for e in events if e.node_id == started.node_id and e.kind in {"node_finished", "node_failed"}]
        assert len(terminals) == 1
    assert events[-1].kind == "run_finished"
    assert sum(e.kind == "run_finished" for e in events) == 1


def test_cancelled_run_has_one_cancel_and_one_terminal_barrier():
    events = cancel_blocked_runtime()
    assert [e.kind for e in events[-2:]] == ["run_cancelled", "run_finished"]
    assert events[-1].public_payload.status == "cancelled"
    assert events[-1].public_payload.stop_reason == "user_cancelled"


def test_capability_events_keep_full_run_identity():
    event = capability_event_from_payment_run()
    assert (event.run_id, event.request_id, event.logical_call_id) == (
        "run_contract", "req_contract", "req_contract:payment-calculation"
    )


def test_event_payloads_never_contain_framework_or_ui_types():
    for event in run_with_events("langgraph", payment_request()):
        assert not recursively_contains_module(event.model_dump(), ("langgraph", "textual", "rich"))


def test_native_and_langgraph_emit_equivalent_progress_events():
    native = normalize_progress(run_with_events("native", payment_request()))
    langgraph = normalize_progress(run_with_events("langgraph", payment_request()))
    assert native == langgraph
```

- [ ] **步骤 2：运行测试确认失败**

```bash
uv run pytest tests/runtime_contracts/test_run_progress_contract.py tests/test_capability_gateway_contract.py -v
```

- [ ] **步骤 3：扩展工作流和 Capability 协议**

增加：

```python
class RunStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StopReason(str, Enum):
    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CAPABILITY_FAILED = "capability_failed"
    SAFETY_BLOCKED = "safety_blocked"
    USER_CANCELLED = "user_cancelled"

class CapabilityRequest(BaseModel):
    run_id: str
    request_id: str
    session_id: str
    capability_name: str
    caller: str
    input: dict[str, Any] = Field(default_factory=dict)
    node_id: str
    logical_call_id: str
    attempt: int = Field(default=1, ge=1)
    runtime_name: str = "native"
    runtime_version: str = "workflow.v1"
```

修正所有 CapabilityRequest 构造点和 tests fixture。

- [ ] **步骤 4：在共享 `_run_stage()` 发布 node lifecycle**

在 Native 和 LangGraph 已共用的 `_run_stage(stages, phase, state)` 周围发布 started/finished/failed。
输入使用 state 摘要，输出使用 StatePatch 摘要；异常分支必须发布 node_failed 后重新抛出或归一化。

- [ ] **步骤 5：由 Runtime 统一发布 run lifecycle**

Native/LangGraph `invoke()` 使用统一 helper：run_started；捕获 `asyncio.CancelledError` 发布
run_cancelled；finally 发布唯一 run_finished。TUI 和 stage 不得发布 run_finished。

- [ ] **步骤 6：工具链发布 capability lifecycle**

ToolExecutorCapabilityGateway 从 request 继承 run identity，发布 started/finished/failed；现有 TraceEvent 保留
兼容字段但不再产生 run_id=None 的新工具事件。

- [ ] **步骤 7：运行 contract 与差分测试**

```bash
uv run pytest tests/runtime_contracts/test_run_progress_contract.py tests/test_capability_gateway_contract.py tests/test_tool_executor.py tests/test_runtime_differential.py -v
```

预期：两 Runtime 生命周期配对；run_finished 唯一且最后；工具身份完整；差分无禁止差异。

- [ ] **步骤 8：Commit**

```bash
git add ananhu_agent/workflow/contracts.py ananhu_agent/capabilities/contracts.py ananhu_agent/runtimes/native/runtime.py ananhu_agent/runtimes/langgraph/runtime.py ananhu_agent/runtimes/native/stages.py ananhu_agent/capabilities/tool_executor_gateway.py ananhu_agent/tools/executor.py tests/runtime_contracts/test_run_progress_contract.py tests/test_capability_gateway_contract.py tests/test_tool_executor.py tests/test_runtime_differential.py
git commit -m "feat(runtime): 发布节点能力与取消生命周期事件"
```

## 任务 4：ObservableModelGateway、reasoning 与 Usage

**文件：** model port/adapters/decorator、model tests、security tests

- [ ] **步骤 1：编写 reasoning/usage 失败测试**

Reasoning 函数：`test_adapter_returns_explicit_reasoning_string`、
`test_adapter_normalizes_missing_null_and_empty_reasoning_to_none`、
`test_reasoning_rejects_non_string_provider_value`、
`test_reasoning_is_excluded_from_dump_and_repr`、
`test_reasoning_at_limit_is_not_truncated`、
`test_reasoning_over_limit_records_original_length_and_truncation`。

Usage 函数：`test_single_reported_provider_usage_status_line`、
`test_multiple_reported_model_results_are_summed`、
`test_mixed_unreported_provider_usage_is_unknown`、
`test_fake_usage_has_explicit_fake_zero_state`、
`test_cache_tokens_are_shown_in_model_detail`、
`test_failed_attempt_without_result_is_not_counted`、
`test_successful_retry_results_are_each_counted`、
`test_inconsistent_provider_total_is_preserved_and_marked`。

边界测试的精确 oracle：reasoning 长度等于上限时 `truncated=False` 且文本逐字一致；超限时
`truncated=True`、`original_chars` 等于原始长度且展示文本不超过上限。cache 明细必须保留 provider
值；无结果的失败调用不增加调用数；两个成功重试结果分别求和；inconsistent total 保留 provider total
并设置 `inconsistent=True`。

```python
@pytest.mark.parametrize("value, expected", [(None, None), ("", None)])
def test_adapter_normalizes_missing_null_and_empty_reasoning_to_none(value, expected):
    result = call_mock_provider(message={"content": valid_output(), "reasoning_content": value})
    assert result.reasoning_content == expected

def test_adapter_returns_explicit_reasoning_string():
    result = call_mock_provider(message={"content": valid_output(), "reasoning_content": "分析步骤"})
    assert result.reasoning_content == "分析步骤"

def test_reasoning_rejects_non_string_provider_value():
    with pytest.raises(ModelGatewayError) as captured:
        call_mock_provider(message={"content": valid_output(), "reasoning_content": {"step": 1}})
    assert captured.value.code is ModelErrorCode.RESPONSE_FORMAT


def test_reasoning_is_excluded_from_dump_and_repr():
    result = model_result(reasoning_content="CANARY_REASONING")
    assert "CANARY_REASONING" not in result.model_dump_json()
    assert "CANARY_REASONING" not in repr(result)


def test_single_reported_provider_usage_status_line():
    line = format_usage_line([provider_result(100, 20, reported=True, latency_ms=1000)], 6100)
    assert "Σ 120 tokens" in line
    assert "20.0 tok/s" in line

def test_mixed_unreported_provider_usage_is_unknown():
    results = [provider_result(100, 20, reported=True), provider_result(0, 0, reported=False)]
    line = format_usage_line(results, 6100)
    assert "tokens unknown" in line
    assert "⚡ --" in line

def test_fake_usage_has_explicit_fake_zero_state():
    assert "fake · 0 tokens" in format_usage_line([fake_result()], 10)

def test_multiple_reported_model_results_are_summed():
    results = [provider_result(100, 20, reported=True), provider_result(50, 10, reported=True)]
    assert "Σ 180 tokens" in format_usage_line(results, 6100)
```

- [ ] **步骤 2：运行测试确认失败**

```bash
uv run pytest tests/test_model_reasoning_contract.py tests/test_model_gateway_contract.py tests/test_tui_presentation.py -v
```

- [ ] **步骤 3：扩展 ModelRequest/ModelResult/ModelUsage**

```python
class ModelRequest(BaseModel):
    session_id: str

class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float | None = None
    currency: str | None = None
    usage_source: str
    reported: bool = False

class ModelResult(BaseModel):
    output: dict[str, Any]
    provider: str
    model: str
    profile: str
    finish_reason: str | None = None
    provider_request_id: str | None = None
    usage: ModelUsage
    latency_ms: int = 0
    attempt: int = 1
    reasoning_content: str | None = Field(default=None, exclude=True, repr=False)
```

同步修正所有 ModelRequest 构造点和 fixture。ObservableModelGateway 直接从 request 获得完整
run/request/session/node/logical-call 身份，不使用 run-scoped 隐式全局状态。

Fake 使用 `reported=False, usage_source="fake"`；OpenAI adapter 仅当 usage 是合法 dict 且包含 provider
token 字段时 `reported=True`。

- [ ] **步骤 4：实现 ObservableModelGateway**

```python
class ObservableModelGateway:
    def __init__(
        self,
        inner: ModelGateway,
        events: RunEventSink,
        sanitizer: TransientSanitizer,
    ) -> None:
        self.inner = inner
        self.events = events
        self.sanitizer = sanitizer

    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        self.events.publish(model_started_event(request, self.sanitizer.model_input(request)))
        try:
            result = await self.inner.generate_structured(request)
        except ModelGatewayError as exc:
            self.events.publish(model_failed_event(request, exc))
            raise
        self.events.publish(model_finished_event(
            request,
            result,
            transient_reasoning=self.sanitizer.reasoning(result.reasoning_content),
        ))
        return result
```

持久化 public payload 只含 reasoning available/length/truncated；stage 删除重复 model started/finished。

- [ ] **步骤 5：实现 Usage 聚合真值表**

在 `presentation.py` 实现接收 `list[ModelResult]` 的 `aggregate_usage()` 和 `format_usage_line()`；
latency 从 ModelResult 读取。provider 任一未报告时总量
unknown、速度 `--`，已知调用只在明细出现；inconsistent total 保留并标记。

- [ ] **步骤 6：reasoning 全路径零落盘测试**

运行一次真实 Runtime mock provider，将 `CANARY_REASONING` 放入 response，扫描：ModelResult dump/repr、
AgentMessage、WorkflowState、TaskState、RunReport、SessionState、trace、badcase、eval/differential artifact。

```bash
uv run pytest tests/test_model_reasoning_contract.py tests/test_tui_security.py -v
```

预期：全部 PASS；canary 仅存在于测试进程内的瞬态断言对象。

- [ ] **步骤 7：Commit**

```bash
git add ananhu_agent/ports/model_gateway.py ananhu_agent/infrastructure/models/openai_compatible.py ananhu_agent/infrastructure/models/fake.py ananhu_agent/models/observable_gateway.py ananhu_agent/runtime.py ananhu_agent/runtimes/native/stages.py ananhu_agent/agents/intent_router.py ananhu_agent/cli/tui/presentation.py tests/test_model_reasoning_contract.py tests/test_model_gateway_contract.py tests/test_intent_router_agent.py tests/test_tui_presentation.py tests/test_tui_security.py
git commit -m "feat(model): 增加可观测 reasoning 与 usage 语义"
```

## 任务 5：`other` 无工具路径与非空错误语义

**文件：** stages/rules/contracts、`tests/test_other_intent_flow.py`、runtime contracts

- [ ] **步骤 1：编写失败测试**

权威 pytest 函数为：`test_greeting_returns_exact_capability_message_without_tools[native|langgraph]`、
`test_non_domain_other_invites_rewrite_without_tools[native|langgraph]`、
`test_all_real_runtime_stop_paths_have_visible_messages`、
`test_cli_ask_never_prints_blank_result`。

```python
@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_greeting_returns_exact_capability_message_without_tools(runtime_name):
    result, events = invoke_with_events(runtime_name, "你好")
    assert result.final_answer == "你好，我是安安虎工伤咨询助手。你可以咨询工伤认定、劳动能力鉴定和待遇测算问题。"
    assert result.status is RunStatus.COMPLETED
    assert not [e for e in events if e.kind.startswith("capability_")]

@pytest.mark.parametrize("runtime_name", ["native", "langgraph"])
def test_non_domain_other_invites_rewrite_without_tools(runtime_name):
    result, events = invoke_with_events(runtime_name, "你会写代码吗？")
    assert "请改写为工伤相关问题" in result.final_answer
    assert not [e for e in events if e.kind.startswith("capability_")]

@pytest.mark.parametrize("runtime_scenario", REAL_STOP_SCENARIOS)
def test_all_real_runtime_stop_paths_have_visible_messages(runtime_scenario):
    result = runtime_scenario.invoke()
    assert result.final_answer or result.clarification_question or result.error_message
```

- [ ] **步骤 2：运行测试确认失败**

```bash
uv run pytest tests/test_other_intent_flow.py tests/runtime_contracts/test_native_runtime_contract.py -v
```

- [ ] **步骤 3：实现 other 计划与 compose**

`plan` 对 `intent=other` 生成 `route_agents=[]、required_tools=[]`；execute 返回空 capability patch；
compose 生成确定性能力说明；safety 仍执行；最终 completed。非问候 other 增加“请改写为工伤相关问题”。

- [ ] **步骤 4：统一停止原因到可见消息**

新增纯函数 `visible_result_message(result)`，ask 与 TUI 共用；任何空值组合转成结构化内部错误文案，
不允许 `typer.echo(None)` 或空 Textual Markdown。

- [ ] **步骤 5：运行流程回归**

```bash
uv run pytest tests/test_other_intent_flow.py tests/runtime_contracts/test_native_runtime_contract.py tests/test_orchestrator_vertical_slice.py tests/test_cli_ask.py -v
```

- [ ] **步骤 6：Commit**

```bash
git add ananhu_agent/runtimes/native/stages.py ananhu_agent/orchestrator/rules.py ananhu_agent/workflow/contracts.py ananhu_agent/cli/main.py tests/test_other_intent_flow.py tests/runtime_contracts/test_native_runtime_contract.py tests/test_orchestrator_vertical_slice.py tests/test_cli_ask.py
git commit -m "feat(flow): 增加 other 无工具回复与非空错误语义"
```

## 任务 6：TUI 展示模型、脱敏与单轮 Widget

**文件：** `presentation.py`、turn/run inspector widgets、styles、presentation tests

- [ ] **步骤 1：编写展示失败测试**

逐项函数：`test_expanding_one_tree_item_does_not_change_siblings`、
`test_mouse_and_keyboard_toggle_the_same_item`、`test_raw_json_toggle_only_changes_selected_item`、
`test_long_json_is_truncated_with_original_length`、`test_json_detail_scrolls_inside_fixed_region`、
`test_reasoning_node_is_absent_when_provider_returns_none`、
`test_nested_secret_sanitizer_masks_keys_and_configured_values`、
`test_sanitizer_masks_query_headers_and_case_variants`、
`test_sanitized_provider_error_never_contains_canary`、
`test_non_sensitive_environment_values_are_preserved`。

```python
def test_expanding_one_tree_item_does_not_change_siblings():
    model = inspector_model(sample_run_events())
    model.toggle("understand.input")
    assert model.item("understand.input").expanded is True
    assert model.item("understand.output").expanded is False


def test_nested_secret_sanitizer_masks_keys_and_configured_values():
    canary = secrets.token_urlsafe(24)
    value = {"headers": {"Authorization": f"Bearer {canary}"}, "items": [{"token": canary}], "home": "/home/xukai"}
    clean = sanitize(value, configured_secrets={canary})
    assert canary not in json.dumps(clean)
    assert clean["home"] == "/home/xukai"


def test_long_json_is_truncated_with_original_length():
    view = json_view({"content": "x" * 20_000}, max_chars=2_000)
    assert view.truncated is True
    assert view.original_chars > len(view.text)
```

- [ ] **步骤 2：运行测试确认失败**

```bash
uv run pytest tests/test_tui_presentation.py tests/test_tui_security.py -v
```

- [ ] **步骤 3：实现集中 presentation**

`presentation.py` 只含纯 Python/Pydantic 展示模型、递归脱敏、裁剪、Usage 格式化和 RunEventReducer；
Textual widgets 不重复处理安全规则。

- [ ] **步骤 4：实现单轮与检查器 Widget**

`TurnWidget` 按 user -> inspector -> assistant Markdown -> usage 排列。`RunInspector` 使用单个 Textual
Tree，层级为 node/model/tool/input/output/reasoning；展开内容用 Syntax/ScrollableContainer，不为每种节点拆文件。

- [ ] **步骤 5：实现 80 列 TCSS**

页面级 `overflow-x: hidden`；输入固定底部；JSON 区局部 `overflow-x: auto`；状态栏不覆盖输入。

- [ ] **步骤 6：运行展示测试**

```bash
uv run pytest tests/test_tui_presentation.py tests/test_tui_security.py -v
```

- [ ] **步骤 7：Commit**

```bash
git add ananhu_agent/cli/tui/presentation.py ananhu_agent/cli/tui/widgets/turn.py ananhu_agent/cli/tui/widgets/run_inspector.py ananhu_agent/cli/tui/styles.tcss tests/test_tui_presentation.py tests/test_tui_security.py
git commit -m "feat(cli): 增加单栏运行检查器组件"
```

## 任务 7：Textual App、实时 worker 与旧 Chat 能力迁移

**文件：** TUI app/modals、CLI main、CLI/Pilot tests

- [ ] **步骤 1：编写 Pilot 失败测试**

函数为：`test_chat_updates_events_live_and_collapses_after_terminal_barrier`、
`test_double_enter_only_invokes_runtime_once`、
`test_retry_keeps_request_id_and_changes_run_id`、
`test_cancel_waits_for_terminal_barrier_and_reaps_worker`、
`test_manual_expansion_survives_normal_completion`、
`test_failed_path_forces_expansion_over_manual_collapse`、
`test_sequence_gap_stops_spinner_and_keeps_local_failure`、
`test_ctrl_j_inserts_newline_without_sending`。

```python
@pytest.fixture
def app_runtime_pair(tmp_path):
    runtime = BarrierRuntime()
    app = AnanhuChatApp(runtime_factory=lambda _: runtime, runtime_dir=tmp_path)
    return app, runtime

@pytest.mark.asyncio
async def test_chat_updates_events_live_and_collapses_after_terminal_barrier(app_runtime_pair):
    app, runtime = app_runtime_pair
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.click("#input")
        await pilot.press(*"你好")
        await pilot.press("enter")
        await runtime.publish_node_started()
        assert app.query_one(RunInspector).running_node == "understand"
        await runtime.finish()
        await pilot.pause()
        assert app.query_one(TurnWidget).inspector_collapsed is True


@pytest.mark.asyncio
async def test_double_enter_only_invokes_runtime_once(app_runtime_pair):
    app, runtime = app_runtime_pair
    async with app.run_test() as pilot:
        await type_query(pilot, "四川十级工伤")
        await pilot.press("enter", "enter")
        assert runtime.invoke_count == 1


@pytest.mark.asyncio
async def test_retry_keeps_request_id_and_changes_run_id(app_runtime_pair):
    app, runtime = app_runtime_pair
    async with app.run_test() as pilot:
        first = await submit_and_finish_failure(app, runtime, pilot)
        await pilot.press("ctrl+r")
        second = app.latest_turn
        assert second.request_id == first.request_id
        assert second.run_id != first.run_id


@pytest.mark.asyncio
async def test_cancel_waits_for_terminal_barrier_and_reaps_worker(app_runtime_pair):
    app, runtime = app_runtime_pair
    async with app.run_test() as pilot:
        await start_blocked_run(runtime, pilot)
        await pilot.press("ctrl+c")
        assert app.active_worker is None
        assert app.latest_turn.status == "cancelled"
        assert app.latest_turn.spinner_visible is False

@pytest.mark.asyncio
async def test_ctrl_j_inserts_newline_without_sending(app_runtime_pair):
    app, runtime = app_runtime_pair
    async with app.run_test() as pilot:
        await type_query(pilot, "第一行")
        await pilot.press("ctrl+j")
        await type_query(pilot, "第二行")
        assert app.query_one("#input", TextArea).text == "第一行\n第二行"
        assert runtime.invoke_count == 0
```

其余 async Pilot 测试复用同一 fixture，并保持全部按键操作在自己的 `run_test()` 上下文内。

- [ ] **步骤 2：迁移旧 chat 行为测试**

将 `test_cli_chat.py` 和 `test_cli_feedback_badcase.py` 的逐行 CliRunner 测试改为 Pilot：

- `test_tui_reuses_session_and_increments_turn`：session 复用且 turn 为 1,2。
- `test_ctrl_n_starts_new_session_and_resets_turn`：Ctrl+N 更换 session 且 turn 重置。
- `test_ctrl_l_clears_screen_without_changing_persisted_state`：不改 session、turn、trace/session state 文件。
- `test_f1_f2_f3_f4_open_expected_modals`：帮助、上下文、trace、badcase modal 可打开关闭。
- `test_tui_good_and_bad_feedback_preserve_existing_semantics`：good 可见确认；bad 写入 badcase JSONL。

- [ ] **步骤 3：运行测试确认失败**

```bash
uv run pytest tests/test_tui_app.py tests/test_cli_chat.py tests/test_cli_feedback_badcase.py -v
```

- [ ] **步骤 4：实现 AnanhuChatApp**

实现 Header、VerticalScroll 会话区、TextArea、Footer；worker 调用 Runtime，独立 consumer 读取 queue。
输入运行中 disabled；Ctrl+C 取消并等待最多 2 秒；Ctrl+N/L/R 保持规格身份语义；Enter 发送，
Shift+Enter/Ctrl+J 换行。

- [ ] **步骤 5：实现 modal/action 能力**

F1 help、F2 context、F3 trace identity、F4 badcase/feedback；复用现有 BadcaseStore，不复制业务逻辑。

- [ ] **步骤 6：替换 `chat` 入口并隔离 TTY 检查**

`chat` 函数内延迟导入 `AnanhuChatApp`。只有 chat 检查 stdin/stdout TTY 和 TERM；失败时 stderr 输出
“ananhu-agent chat requires an interactive ANSI terminal”并退出 2。ask/eval/version 不导入 Textual app。

- [ ] **步骤 7：运行 Pilot 测试**

```bash
uv run pytest tests/test_tui_app.py tests/test_cli_chat.py tests/test_cli_feedback_badcase.py -v
```

- [ ] **步骤 8：Commit**

```bash
git add ananhu_agent/cli/tui/app.py ananhu_agent/cli/tui/modals.py ananhu_agent/cli/main.py tests/test_tui_app.py tests/test_cli_chat.py tests/test_cli_feedback_badcase.py
git commit -m "feat(cli): 使用 Textual TUI 替换 chat"
```

## 任务 8：80×24、真实 PTY、安全扫描与全量验收

**文件：** terminal/security tests、任务总计划完成记录

- [ ] **步骤 1：实现布局与 resize 测试**

具体函数：`test_80x24_regions_do_not_overlap`、`test_long_content_does_not_create_page_horizontal_scroll`、
`test_json_detail_has_local_horizontal_scroll`、`test_resize_during_run_preserves_regions_and_input`。

Pilot `size=(80,24)` 注入中文、Markdown 表格、120 字符无空格 token、四层树和深层 JSON。断言：

```python
header = app.query_one("#header").region
conversation = app.query_one("#conversation").region
input_region = app.query_one("#input").region
footer = app.query_one("#footer").region
assert header.bottom <= conversation.y
assert conversation.bottom <= input_region.y
assert input_region.bottom <= footer.y
assert app.query_one("#conversation").virtual_size.width <= app.screen.size.width
assert app.query_one("#json-detail").styles.overflow_x == "auto"
```

运行中 resize 到 100x30 再回 80x24，重复 region 断言；保存
`.ananhu-runtime/acceptance/tui-80x24.svg` 与 `tui-resized.svg`。这些是 ignored 本地验收 artifact，不提交 Git。

- [ ] **步骤 2：实现真实 PTY 测试**

具体函数与精确 oracle：

- `test_chat_starts_and_ctrl_c_exits_in_real_pty`：发送 `\x03`，10 秒内 exit 0，无 Traceback。
- `test_sigwinch_resize_keeps_chat_alive`：设置 80x24、再 100x30 并发送 SIGWINCH，进程仍运行且可退出。
- `test_term_dumb_exits_two_with_clear_message`：exit 2，stderr 含 interactive ANSI terminal。
- `test_non_tty_exits_two_and_reaps_process`：stdin pipe 模式 exit 2，`poll()` 非 None。

使用 `subprocess.Popen` + PTY：正常启动/退出、resize、TERM=dumb、非 TTY。Ctrl+J 已由可注入
BarrierRuntime 的 Pilot 精确验证。每个进程
`communicate(timeout=10)`，finally kill/wait，断言无存活子进程。TERM=dumb/非 TTY 精确断言 exit 2；
正常 chat 无 traceback。

- [ ] **步骤 3：实现运行时随机 canary 扫描 `SEC-010`**

测试运行时用 `secrets.token_urlsafe(32)` 生成 canary，注入 reasoning、Prompt、tool result、header、URL、
SecretStr 和 provider error。扫描 Pilot export、captured log/traceback、`.ananhu-runtime/**/*` 和
`git grep` 输出，全部零命中。canary 不得作为源码 fixture 字面量。

- [ ] **步骤 4：运行 TUI 验收测试**

```bash
uv run pytest tests/test_run_progress_events.py tests/runtime_contracts/test_run_progress_contract.py tests/test_model_reasoning_contract.py tests/test_other_intent_flow.py tests/test_tui_presentation.py tests/test_tui_app.py tests/test_tui_terminal.py tests/test_tui_security.py -v
```

预期：全部 PASS；真实 provider smoke 未显式开启时可 skip。

- [ ] **步骤 5：运行全量测试与非 TTY CLI 回归**

```bash
uv run pytest -v
uv run ananhu-agent version
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
uv run ananhu-agent eval data/eval/eval_cases.jsonl --runtime both
```

预期：pytest 零失败；version/ask/eval 在非 TTY 下 exit 0；30 条 eval 全通过；differential 为
`equivalent=30, different=0`；metrics、trace、differential JSON 可解析且无 reasoning/secret。

- [ ] **步骤 6：真实 TUI 手工 smoke**

在 PTY 中运行：

```bash
set -a
source .env
set +a
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy
uv run ananhu-agent chat
```

验证：输入“你好”得到能力说明；输入待遇问题得到回答；执行过程实时更新；节点/工具/model
input/output/reasoning 可独立展开；AI 消息末尾显示聚合 Usage；Ctrl+C 正常退出。

- [ ] **步骤 7：更新总演进计划完成记录**

在 `docs/superpowers/plans/2026-07-10-framework-neutral-langgraph-evolution.md` 新增任务 35：Textual Chat TUI，记录上述命令和结果，不覆盖既有 KnowledgeGateway 任务 33/Smoke 任务 34。

- [ ] **步骤 8：Commit**

```bash
git add tests/test_tui_app.py tests/test_tui_terminal.py tests/test_tui_security.py docs/superpowers/plans/2026-07-10-framework-neutral-langgraph-evolution.md
git commit -m "test(cli): 验收 Textual TUI 真实终端交互"
```

## 最终交付检查

- [ ] `git diff --check` 通过。
- [ ] `git status --short --branch` 只显示允许的 ignored 本地 `.env`、`config/models.yaml` 和 runtime artifact。
- [ ] `git log --oneline -12 --decorate` 包含 v0.7、事件协议、reasoning/Usage、other、TUI 和验收提交。
- [ ] `rg -n "textual|rich" ananhu_agent --glob '*.py'` 只在 `cli/tui` 和 CLI 延迟导入处命中；测试显式导入除外。
- [ ] 随机 canary 不存在于 Git、trace、state、report、badcase、eval、differential、屏幕导出或测试日志。
- [ ] 向用户汇报改动范围、验证证据和待合并分支，等待明确确认后才提交最终未提交改动并合并回 `mvp`。
