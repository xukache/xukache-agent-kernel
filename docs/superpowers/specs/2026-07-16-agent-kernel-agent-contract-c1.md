# Agent Kernel C1 Agent 公共调用边界设计

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | C1：定义 AgentDefinition、AgentInput 与 AgentResult |
| 日期 | 2026-07-16 |
| 状态 | 已完成 |
| 任务分支 | `task/c1-agent-contract` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.26` |
| 前置任务 | B6 已完成，RD-001 已通过 |

本记录保存 C1 已由用户逐项确认的公共调用边界。完整当前规格仍以
[`DEV_SPEC.md`](../../../DEV_SPEC.md) 为事实源；本记录不替代完整规格，也不把
C2-C4 的执行行为提前写入 C1。

## 2. 目标与方案

C1 回答：

> Agent 的长期装配、单次调用和最终结果如何使用三个不同对象表达？

采用渐进式最小契约：

```text
AgentDefinition -> 长期只读装配
AgentInput      -> 本次调用数据
AgentResult     -> 本次调用最终结构化结果
```

C1 不通过 `Any`、通用 capability 容器或空占位协议提前定义 Tool 和 Memory。
允许 Tools 由 D 阶段加入 AgentDefinition，Memory Policy 和 scope 上下文由 E
阶段加入对应 Definition / Input。

未采用的方案：

- 一次定义包含 Tool、Memory 的完整 AgentDefinition：会提前冻结 D、E 契约。
- 通用 capability 容器：会削弱类型约束并引入当前没有使用证据的抽象。

## 3. AgentDefinition

```python
@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
    eq=False,
)
class AgentDefinition:
    definition_id: str
    revision: str
    instructions: str
    model: Model
    max_model_rounds: int
```

字段语义：

| 字段 | 所有权与规则 |
|---|---|
| `definition_id` | Definition 稳定标识；不另设重复的 agent_id |
| `revision` | 装配变化时由 Application / Composition Root 更新 |
| `instructions` | Agent 长期指令；必须为非空、非纯空白字符串 |
| `model` | 已注入且满足 `Model` Protocol 的运行对象 |
| `max_model_rounds` | 必须显式传入的正整数执行上限 |

构造只检查本地装配不变量，不访问 Provider 网络，不验证凭证，也不执行模型能力
预检。`bool` 不作为合法 `max_model_rounds`。Definition 不保存本次 input、
output_schema、run_id、Provider 配置、Tool Call 历史或 Result。

## 4. AgentInput

```python
class AgentInput(KernelSchema):
    input: str | JsonObject
    output_schema: JsonObject | None = None
    application_metadata: JsonObject = Field(default_factory=dict)
```

字段语义：

| 字段 | 所有权与规则 |
|---|---|
| `input` | 本次任务文本或结构化对象；文本不得为空或纯空白 |
| `output_schema` | 本次调用期望的可选 JSON Schema，由 C2 映射到 ModelRequest |
| `application_metadata` | 调用方附加的受控元数据，不自动进入 Model |

结构化空对象允许作为 input。三个 JSON 边界都必须遵守 A2 的严格类型和防御性复制
规则；调用方在构造后修改原始 dict / list 不能改变 AgentInput。

`application_metadata` 与 `runtime_metadata`、`provider_metadata` 分域。C1 不为它
定义核心逻辑消费者，C2 也不能把完整 metadata 无条件写入 Prompt 或 ModelRequest。
run_id、deadline 和 cancellation 属于未来 RunContext。

## 5. AgentResult

```python
class AgentStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStopReason(str, Enum):
    COMPLETED = "completed"
    MAX_MODEL_ROUNDS = "max_model_rounds"
    ERROR = "error"
    CANCELLED = "cancelled"


class AgentResult(KernelSchema):
    status: AgentStatus
    output: str | JsonObject | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage
    model_id: str | None = None
    stop_reason: AgentStopReason
    error: ErrorInfo | None = None
```

状态组合：

| status | output | error | stop_reason | model_id |
|---|---|---|---|---|
| `succeeded` | 必填 | 必须为空 | `completed` | 必填 |
| `failed` | 必须为空 | 必填 | `error` 或 `max_model_rounds` | 可为空 |
| `cancelled` | 必须为空 | 必填 | `cancelled` | 可为空 |

`MAX_MODEL_ROUNDS` 单独表达 Agent 在 Model / Tool 均可能正常时，因为执行策略上限
而确定性停止。具体失败证据仍由 `error.code == "agent.limit"` 表达。这样可以分别
观察循环控制原因和错误分类，不需要解析 message。

`tool_calls` 复用 B1 已确认的 Provider Neutral `ToolCall`，只保存模型调用意图；
C1 不执行 Tool。`usage` 使用 B1 已确认的 `Usage`，C3-C4 负责在真实执行中生成或
累计。成功结果必须提供实际 `model_id`。

## 6. 错误边界

共享失败证据：

```python
class ErrorInfo(KernelSchema):
    code: str
    message: str
    source: ErrorSource
    retryable: bool
    details: JsonObject = Field(default_factory=dict)
```

ErrorInfo 的 `code` 保存模块拥有的 `str Enum` 序列化值，避免共享 contracts
反向依赖所有 Core 的错误枚举。

C1 Agent 错误码：

| 错误码 | 含义 |
|---|---|
| `agent.limit` | 达到 Agent 执行上限 |
| `agent.cancelled` | Agent 调用被取消 |
| `agent.internal` | Agent 边界无法归类的内部失败 |

ModelError 转换时保留 `model.provider`、`model.timeout`、`model.rate_limit`、
`model.format` 或 `model.cancelled`，并把 source 标记为 Model。C1 只定义结果
边界；实际 ModelError 转换属于 C3，limit 产生逻辑属于 C4。

合法运行前的无效 Definition 或 Input 直接抛出 ValueError 或 Pydantic
ValidationError，不构造 failed AgentResult。

## 7. 文件职责

| 文件 | C1 职责 |
|---|---|
| `src/agent_kernel/contracts/schemas.py` | KernelSchema 和共享 JSON 类型 |
| `src/agent_kernel/contracts/errors.py` | KernelError、ErrorInfo、ErrorSource |
| `src/agent_kernel/contracts/__init__.py` | 共享契约公开导出 |
| `src/agent_kernel/model/schemas.py` | 改用共享 Schema / JSON 类型，保持 Model 行为不变 |
| `src/agent_kernel/agent/definition.py` | AgentDefinition |
| `src/agent_kernel/agent/schemas.py` | AgentInput、AgentResult 和状态枚举 |
| `src/agent_kernel/agent/errors.py` | AgentErrorCode |
| `src/agent_kernel/agent/__init__.py` | Agent 公共导入入口 |

C1 不创建 `agent/engine.py`，不实现 ModelRequest Builder、Model 调用、Tool、
Memory、Runtime 或真实对话场景。

## 8. 测试与验收

确定性测试：

| 测试 | 证明内容 |
|---|---|
| `tests/unit/contracts/test_error_info.py` | ErrorInfo 严格校验、不可变和 JSON 序列化 |
| `tests/unit/agent/test_agent_definition.py` | Definition 冻结、本地校验和 Model Protocol |
| `tests/unit/agent/test_agent_schemas.py` | Input 防御性复制和 Result 状态组合 |
| `tests/unit/model/` | 提升共享 Schema 后 Model 契约不回归 |
| `tests/architecture/` | Agent 不依赖外围层或 Provider SDK |

验证命令：

```bash
uv run pytest -q tests/unit/contracts
uv run pytest -q tests/unit/agent
uv run pytest -q tests/unit/model
uv run pytest -q tests/architecture
uv run pytest -q
uv build
git diff --check
```

C1 关联 K-001、K-007，但只建立这些验收所需的公共类型前置条件，不声明 Agent
模块完成，不运行 RD-002。RD-002 由 C5 使用真实 Provider 完成。

## 9. 文档与版本影响

- 更新完整 `DEV_SPEC.md`，把 C1 设为进行中并写入已确认字段。
- 更新公共契约导航、架构摘要、确认索引和架构 changelog。
- 不新增 `docs/dev-spec/versions/`：C1 属于当前 v0.26 里程碑内的逐模块确认。
- 不新增 `docs/architecture/versions/`：六个 Core、依赖方向、所有权和部署边界
  均未改变。
- 用户确认 C1 实现结果前，不把 C1 标记为完成，不提交实现完成状态，也不合并回
  `architecture`。
