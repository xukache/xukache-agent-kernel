# 公共契约

公共契约按“行为、装配、数据、失败、状态”分层表达。

## 类型映射

| 语义 | Python 表达 | 用途 |
|---|---|---|
| 行为契约 | `typing.Protocol` | Model、Tool、Memory、Runtime 等可替换能力 |
| 只读装配 | frozen `dataclass` | AgentDefinition、WorkflowDefinition、ToolDefinition 等 |
| 结构化数据 | 严格 Pydantic Schema | Input、Result、Event、State 和跨 Adapter 数据 |
| 运行时失败 | `KernelError` | Python 调用栈中的中断和传播 |
| 失败证据 | `ErrorInfo` | Result、Event 和测试中的可序列化错误 |
| 稳定状态 | `str Enum` | status、stop_reason、event type 和 error code |
| 共享实现 | ABC | 仅在存在真实共享实现时内部使用 |

## Definition

Definition 描述组件如何被只读装配：

```python
@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
    eq=False,
)
class ComponentDefinition:
    ...
```

- 必须提供 `definition_id` 和 `revision`。
- 可以引用 Protocol 实例和函数包装器，因此不承诺整体 JSON 序列化。
- 不保存本次输入、run_id、State、Result、凭证或 Provider SDK 配置。
- 恢复数据只保存可序列化的 `DefinitionRef`。

## Schema Model

Input、Result、Event 和 State 继承统一配置，但不继承万能业务字段：

```python
class KernelSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )
```

- 每个模块定义自己的 Input 和 Result。
- Schema 不包含 Protocol、callable、SDK 对象、凭证或内部 Exception。
- 已知结构使用明确 Schema；开放 JSON 只用于确实开放的数据。
- Input 和 State 必须稳定 JSON 序列化；State 必须通过 JSON 往返保持语义等价。

## Result 与 Event

- Result 表达一次模块调用的最终结构化结果，不创建万能 `KernelResult`。
- 状态组合由 model validator 约束：成功无错误，失败有 `ErrorInfo`，暂停有 State 或稳定引用。
- Event 使用一层公共信封、稳定 `type` 和判别联合。
- Event 只能追加，按 sequence 排序，并且每个 Run 只有一个 Terminal Event。
- Streaming 结束后只创建一次最终 Result，最终内容必须与已消费增量一致。

## Model 数据协议

B1 已确认 `agent_kernel.model` 的第一组 Provider Neutral Schema：

| 类型 | 职责 |
|---|---|
| `ModelRequest` | 携带 instructions、input、上下文、Memory 投影、Tool Schema、输出 Schema 和运行元数据 |
| `ModelResponse` | 携带文本、结构化输出、Tool Call、usage、finish_reason 和受控 Provider metadata |
| `ToolSchema` | 描述 Model 可见的工具，不包含可执行对象 |
| `ToolCall` | 表达 Model 生成的调用意图，不包含 Python callable |
| `Usage` | 归一化 input、output、total token 数 |

这些对象使用 `frozen=True`、`extra="forbid"` 和 `strict=True`，可以稳定
JSON 序列化。`ModelResponse` 约束 `tool_call` 结束原因必须有 Tool Call，
`stop` 结束原因不得包含 Tool Call。B1 只定义数据，不定义 Model Protocol、
Provider 错误或 `generate / stream` 行为。

## Model 行为契约与错误

B2 已确认 `Model` Protocol：

```python
async def generate(request: ModelRequest) -> ModelResponse
def stream(request: ModelRequest) -> AsyncIterator[ModelStreamChunk]
```

`generate` 返回一次完整响应；`stream` 返回按产生顺序消费的一次性异步
增量流。`ModelStreamChunk` 可以携带文本增量、结构化增量、Tool Call 增量、
usage 或 finish_reason，但不携带 Provider SDK 类型。

Model 运行时错误统一使用 `ModelErrorCode`：

| 错误码 | 语义 |
|---|---|
| `model.provider` | Provider 调用或响应不可用 |
| `model.timeout` | 超过调用时限 |
| `model.rate_limit` | Provider 限流 |
| `model.format` | 请求或响应格式不满足契约 |
| `model.cancelled` | Model 调用被取消 |

`ModelError` 继承公共 `KernelError`，其 `retryable` 只描述错误属性，不自动触发重试；重试策略由后续
Runtime / Execution 任务治理。B2 不实现 Provider 转换、RunContext 或取消令牌。

## Agent 公共调用边界

C1 已确认渐进式最小 Agent 契约：

| 类型 | 当前字段 |
|---|---|
| `AgentDefinition` | definition_id、revision、instructions、model、max_model_rounds |
| `AgentInput` | input、output_schema、application_metadata |
| `AgentResult` | status、output、tool_calls、usage、model_id、stop_reason、error |

AgentDefinition 使用 frozen dataclass，并只检查本地装配不变量。AgentInput 和
AgentResult 使用严格、不可变 Schema。AgentStatus 包含 succeeded、failed 和
cancelled；AgentStopReason 包含 completed、max_model_rounds、error 和 cancelled。

达到最大模型轮次属于确定性策略停止：AgentResult 使用 failed +
max_model_rounds，并通过 `agent.limit` 提供错误证据。Model 失败继续保留
`model.*` 错误码，不转换成模糊的 agent.model。

C1 不定义 Tool 和 Memory 占位类型；D、E 阶段在各自确认后扩展 AgentDefinition
和 AgentInput。C1 也不实现 ModelRequest 组装或 Agent 推理循环。

## Error

```text
Provider / Backend Exception
  -> Adapter 映射为 KernelError
  -> 明确模块边界转换为 ErrorInfo
  -> failed Result
  -> failure Event
```

`ErrorInfo` 至少表达稳定 code、公开 message、source、retryable 和脱敏 details。`retryable=True` 只是错误属性，不代表一定执行重试。

## State

- 第一阶段主要公开 State 是 WorkflowState，不创建万能 `KernelState`。
- State 每次推进创建新实例，不原地修改。
- State 可以包含 DefinitionRef、结构化步骤结果或引用，不包含运行对象和进程内资源。
- `definition_ref.revision` 与 `state_schema_version` 分别管理定义和状态结构版本。
- `checkpoint_id` 可以进入 State；一次性 `resume_token` 不能进入 State。

## Memory 概念契约

E1 尚未开始，因此本分册不冻结最终 Python 字段，但以下公共语义已经确认：

- Memory 是按 scope 分区的统一 Protocol，不是每个 Session 一个独立 Core 实例。
- scope 至少能够稳定表达会话级、用户级和项目 / 共享级边界。
- Agent Memory Policy 明确允许读取的 scope 集合、默认写入目标、排序、去重、预算
  和授权规则。
- `MemoryItem` 保存提炼后的可复用内容、来源、创建时间和可选元数据，默认不保存
  完整聊天历史。
- MemoryItem 的来源可以指向 run、session 或前序 MemoryItem；跨 scope 提升必须创建
  新条目并保留来源链。
- read、search 和 write 不允许隐式跨 scope；Adapter 不自行合并 scope。
- WorkflowState、Checkpoint、Trace、UI 历史、完整 Tool Call 历史和业务数据库事实
  不进入 MemoryItem。
- 当前 `ModelMemoryItem` 只是 ModelRequest 的只读投影，不替代 E1 的完整
  `MemoryItem` 和 scope 契约。

完整规则和示例以 A2 确认记录为准；A3 已确认 `agent_kernel` 及其稳定子包为公开导入边界；B1 已确认 Model 数据协议，B2 已确认 Model 行为和错误语义；其他字段、枚举和错误捕获层级由 B-G 对应任务确认。
