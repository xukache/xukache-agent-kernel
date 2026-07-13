# Agent Kernel A2 公共类型表达策略

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | A2：确认公共类型表达策略 |
| 日期 | 2026-07-13 |
| 状态 | 已完成 |
| 任务分支 | `task/a2-public-type-strategy` |
| 当前规格 | `DEV_SPEC v0.25` |

本记录保存 A2 已确认的设计、后续任务仍需细化的字段边界，以及逐项确认期间执行过的“不提前标记完成、不提前提交、不提前合并”门禁。

## 2. 已确认的总体策略

采用分层混合类型策略：

| 类型工具 | 当前职责 |
|---|---|
| `Protocol` | 表达 Model、Tool、Memory、Runtime 等行为契约 |
| frozen `dataclass` | 表达 Definition 和 Kernel 内部只读装配对象 |
| Schema Model | 表达 Input、Result、Event、State 和跨 Adapter 数据 |
| Exception | 表达 Python 运行时失败传播 |
| Error Schema | 表达可序列化错误证据 |
| `str Enum` | 表达稳定状态、停止原因和事件类型 |
| ABC | 不作为默认公共契约；只有出现真实共享实现时才在内部使用 |

总体边界：

```text
Protocol       -> 对象能做什么
Definition     -> 一个组件如何被只读装配
Schema Model   -> 跨边界传递什么结构化数据
Exception      -> 运行时如何中断和传播失败
Error Schema   -> Result / Event 如何保存失败证据
str Enum       -> 状态和原因如何保持稳定
```

## 3. 已确认的 Definition 类型规则

Definition 是组件的只读装配说明，不是本次调用输入、运行状态或最终结果。

以 Agent 为例：

```text
AgentDefinition
  -> definition_id
  -> revision
  -> instructions
  -> Model Protocol 实例
  -> 允许使用的 Tool 实例
  -> Memory 使用策略
  -> 执行上限
```

Definition 统一采用：

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

参数语义：

| 参数 | 作用 |
|---|---|
| `frozen=True` | 创建后禁止原地修改 |
| `slots=True` | 字段固定，禁止动态增加属性 |
| `kw_only=True` | 构造时必须显式写出字段名 |
| `eq=False` | 不对 Model、Tool 和函数包装器执行结构相等比较 |

每个 Definition 必须提供：

```text
definition_id
revision
```

Definition 身份只能通过 `definition_id + revision` 显式判断。

统一边界：

- Definition 创建后不可原地修改，变更时创建新对象并更新 revision。
- Definition 可以引用 Protocol、函数包装器或其他运行对象。
- Definition 内部集合使用 `tuple`、`frozenset` 或等价不可变值对象。
- Definition 不保存本次用户输入、run_id、WorkflowState 或执行结果。
- Definition 不包含 Provider 密钥和 Provider SDK 配置。
- 包含运行对象的 Definition 不承诺整体 JSON 序列化。
- `__post_init__` 只校验本地装配不变量，不执行 Provider 网络和凭证检查。
- 暂停恢复数据只保存 `DefinitionRef(definition_id, revision)`。
- Application / Composition Root 负责在运行和恢复时重新提供 Definition。
- 恢复时 revision 不一致必须返回明确错误，不能用新版 Definition 猜测恢复旧 State。

DefinitionRef 属于可序列化 Schema Model：

```python
class DefinitionRef(BaseModel):
    definition_id: str
    revision: str
```

Definition 的具体业务字段仍由对应 B-G 任务确认，A2 只冻结公共类型和生命周期规则。

## 4. 已确认的 Input 类型规则

Input 表示某个模块本次调用收到的数据，不保存长期装配、运行状态或最终结果。

第一阶段主要 Input：

```text
AgentInput
WorkflowInput
ToolInput
ModelRequest
RunRequest
```

Input 使用严格、不可变的 Pydantic Schema Model：

```python
class KernelSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )
```

`KernelSchema` 只统一 Schema 配置，不定义 run_id、scope、metadata、provider 等万能字段。

配置语义：

| 配置 | 作用 |
|---|---|
| `frozen=True` | Input 创建后禁止修改 |
| `extra="forbid"` | 拒绝拼错字段和未声明参数 |
| `strict=True` | 禁止错误类型被隐式转换 |

统一边界：

- 每个模块拥有独立 Input，不创建 UniversalInput。
- Input 不重复携带 Definition 中已有的 Model、Tools、Instructions 或 Workflow 拓扑。
- Pydantic frozen 只提供浅层冻结；嵌套 Schema 也必须冻结，集合优先使用 tuple，开放 JSON 不得保留调用方可变引用。
- Input 不包含 Protocol、callable、可执行 Tool、Provider SDK 类型或凭证。
- Input 必须能够稳定序列化为 JSON。
- 公共字段使用明确类型，不使用 `Any` 绕过契约。
- Model 生成的非法 Tool 参数必须形成明确 validation 错误，Kernel 不猜测转换。
- run_id、deadline 和 cancellation 属于 RunContext。
- 运行中产生的数据属于 State、Event 或 Result，不能回填 Input。
- 新的调用数据必须创建新的 Input 和新的 Run。

不同数据的所有权：

| 数据 | 所属对象 |
|---|---|
| 本次 Agent 任务 | `AgentInput` |
| 本次 Workflow 初始数据 | `WorkflowInput` |
| Model 请求内容 | `ModelRequest` |
| Tool 参数 | `ToolInput` |
| run_id、deadline、取消信号 | `RunContext` |
| Model、Tools、Instructions | `AgentDefinition` |
| 流程位置和步骤结果 | `WorkflowState` |
| Provider 凭证和 SDK 配置 | Model Adapter |

Input 的具体字段和嵌套 Schema 仍由对应 B-G 任务确认。

## 5. Function Calling 与 Tool 边界

### 5.1 三种不同对象

Function Calling 不是把 Python 函数直接交给模型。必须区分：

| 对象 | 所在位置 | 职责 |
|---|---|---|
| 可执行 `Tool` | Kernel 运行内存 | 持有公开 Definition，并完成真实 Backend 调用 |
| `ToolDefinition` / Tool Schema | ModelRequest | 告诉 Model 工具名称、说明、参数和治理声明 |
| `ToolCall` | ModelResponse | 表达 Model 希望调用哪个工具以及使用什么参数 |
| `ToolResult` | Tool 执行后 | 表达统一 output、执行元数据或错误 |

固定不等式：

```text
Tool              != ToolDefinition
ToolDefinition    != ToolCall
ToolCall          != ToolResult
Model 看见 Schema != Model 获得 Python callable
```

### 5.2 add_tool 示例

Application 装配一个可执行工具：

```text
add_tool
  -> definition.name = "add"
  -> definition.description = "计算两个整数的和"
  -> definition.input_schema = {a: integer, b: integer}
  -> execute({a, b}) = {result: a + b}
```

AgentDefinition 保存：

```text
tools = (add_tool,)
```

Model 实际只能看到：

```json
{
  "name": "add",
  "description": "计算两个整数的和",
  "parameters": {
    "type": "object",
    "properties": {
      "a": {"type": "integer"},
      "b": {"type": "integer"}
    },
    "required": ["a", "b"]
  }
}
```

Model 返回的是调用意图：

```json
{
  "call_id": "call-001",
  "name": "add",
  "arguments": {
    "a": 37,
    "b": 58
  }
}
```

Kernel 找到内存中的 `add_tool` 并执行，得到：

```json
{
  "call_id": "call-001",
  "output": {
    "result": 95
  },
  "error": null
}
```

### 5.3 完整执行流程

```text
Application 创建 AgentDefinition，并注入可执行 Tools
  -> Agent 提取 ToolDefinition / Tool Schema
  -> Model Adapter 转换为 Provider Tool Schema
  -> Provider 返回 Tool Call
  -> Model Adapter 转换为 Kernel ToolCall
  -> Agent 检查 Tool 是否在当前白名单
  -> Agent 根据 ToolCall.name 找到可执行 Tool
  -> 校验 ToolInput
  -> Runtime / Execution 执行治理
  -> Tool 调用 Backend
  -> 返回 Kernel ToolResult
  -> Agent 把 ToolResult 加入下一次 ModelRequest
  -> Model 生成最终回答或新的 ToolCall
```

### 5.4 职责所有权

| 模块 | 职责 |
|---|---|
| Application | 创建 Tool，并注入 AgentDefinition |
| AgentDefinition | 保存当前 Agent 允许使用的可执行 Tool 白名单 |
| Agent | 构建 Tool Schema、处理 Tool Call 循环、解析允许工具、回传 ToolResult |
| Model Adapter | 在 Kernel Tool Schema / ToolCall 与 Provider SDK 类型之间转换 |
| Model | 只选择工具和生成参数，不执行工具 |
| Runtime / Execution | 提供 RunContext、Guardrail、Permission、Cancellation、Retry 和幂等治理 |
| Tool | 校验统一输入输出契约并完成一次 Backend 调用 |
| Tool Backend | 执行真正的函数、HTTP、数据库、MCP 或本地动作 |

Tool 不自行决定是否再次调用 Model。是否继续 Function Calling 循环只由 Agent 根据 ModelResponse 和执行上限决定。

## 6. 已确认的 Result 类型规则

Result 表示一次模块调用的最终结构化结果：

```text
Input  -> 模块开始执行时收到什么
Event  -> 执行过程中发生了什么
State  -> 可继续执行的当前状态
Result -> 本次模块调用最终得到什么
```

主要公开结果：

```text
ModelResponse
AgentResult
ToolResult
WorkflowResult
RuntimeResult
```

每个模块定义自己的 Result Schema，不创建万能 `KernelResult`。

统一规则：

- Result 继承 KernelSchema，保持 frozen、strict 和 extra forbid。
- 能够以多种终态结束的 Result 使用模块专属 `str Enum` 表达状态。
- 不使用 `success: bool` 混合成功、失败、取消和暂停。
- 各模块只声明自己支持的状态，`paused` 不进入不支持暂停的模块。
- 使用 model validator 检查 status、output、error 和 state 的合法组合。
- 成功结果不能包含 ErrorInfo。
- 失败结果必须包含 ErrorInfo。
- 暂停结果必须包含可恢复 State 或其稳定引用。
- Result 不保存 Provider SDK 类型、凭证、完整 Prompt、完整 Events 或日志副本。
- Result 可以包含归一化 usage、stop_reason、必要调用摘要和事件引用。
- 内部 Exception 在明确模块边界转换为 ErrorInfo。
- Streaming 结束后只创建一次最终 Result，最终内容必须与已消费增量一致。

必须保持：

```text
RuntimeResult != AgentResult
RuntimeResult != WorkflowResult
RuntimeResult != ToolResult
AgentResult   != ToolResult
```

Result 之间可以组合和引用，但不能通过继承收敛成万能结果对象。

状态组合示例：

```text
succeeded -> error 为空，output 满足模块要求
failed    -> error 必须存在
cancelled -> 不能产生 succeeded 或 completed 终态
paused    -> 只用于支持暂停的模块，并携带恢复数据
```

具体状态枚举、必填输出字段和异常捕获层级仍由对应 B-G 任务确认。

## 7. 已确认的 Event 类型规则

Event 表示运行过程中已经发生的结构化事实：

```text
run.started
model.request.started
tool.call.started
tool.call.completed
workflow.paused
run.failed
```

Event 不是 Command、State、Result 或普通调试日志。

采用“公共信封 + 具体事件 + 判别联合”：

```python
class EventEnvelope(KernelSchema):
    event_id: str
    run_id: str
    sequence: int
    occurred_at: datetime
    source: EventSource
```

具体事件拥有稳定 type 和明确字段：

```python
class ToolCallStartedEvent(EventEnvelope):
    type: Literal["tool.call.started"] = "tool.call.started"
    call_id: str
    tool_name: str
    arguments_summary: JsonObject
```

事件联合使用 type 判别：

```python
KernelEvent = Annotated[
    RunStartedEvent
    | ToolCallStartedEvent
    | ToolCallCompletedEvent
    | RunCompletedEvent
    | RunFailedEvent,
    Field(discriminator="type"),
]
```

统一规则：

- Event 继承 KernelSchema，创建后不可修改，只能追加。
- 只共享一层 EventEnvelope，不建立深层事件继承。
- 不使用 `payload: dict[str, Any]` 万能负载。
- Runtime 保证同一 run_id 内 sequence 单调递增。
- Event 顺序以 sequence 为准，occurred_at 统一使用 UTC。
- 并行事件通过 sequence 和 step_id / call_id 等字段表达观察顺序。
- 每个 Run 只能产生一个 Terminal Event。
- cancelled 或 failed 后不能再产生 completed。
- WorkflowState 是暂停恢复的事实源，第一阶段不依靠回放 Events 恢复。
- Result 可以保存事件引用或摘要，但不能复制全部 Events。
- Tool 参数与输出默认只保存脱敏摘要。
- Event 不保存 Provider 密钥、完整敏感 Prompt、Backend 凭证或 Provider 原始响应。

Streaming 增量是否作为具体事件类型由 F3 确认；若进入 Event，仍遵守同一信封和顺序规则。

## 8. 已确认的 Error 类型规则

错误使用双层模型：

```text
KernelError -> Python 运行时中断和传播失败
ErrorInfo   -> Result、Event 和测试证据中的可序列化错误
```

KernelError 只建立少量需要不同捕获边界的领域异常：

```text
KernelError
├── ModelInvocationError
├── ToolExecutionError
├── MemoryOperationError
├── WorkflowExecutionError
├── RuntimeExecutionError
└── KernelCancellationError
```

具体错误差异通过稳定 ErrorCode 表达，不为每个错误码创建异常子类。

ErrorInfo 使用严格 Schema：

```python
class ErrorInfo(KernelSchema):
    code: ErrorCode
    message: str
    source: ErrorSource
    retryable: bool
    details: JsonObject
```

错误转换链：

```text
Provider / Backend Exception
  -> Adapter 映射为 KernelError
  -> 模块边界转换为 ErrorInfo
  -> failed Result
  -> failure Event
```

统一规则：

- Provider SDK Exception 必须在对应 Adapter 边界映射。
- 使用异常链保留内部 cause，但 cause 不进入公开 Schema。
- ErrorCode 使用 Provider Neutral 的分域字符串。
- Provider 原始错误码不能成为 Kernel 公共错误码。
- Exception、traceback、SDK 对象和凭证不能进入 ErrorInfo。
- 无效 Definition 或 Input 构造直接抛出 ValueError / Pydantic ValidationError。
- 只有合法运行中的操作失败才生成 failed Result 和 failure Event。
- `retryable=True` 不等于自动重试。
- 真正重试还必须满足幂等、Retry Policy、次数、deadline 和未取消条件。
- Permission、Schema、Cancellation 和非幂等副作用失败不得自动重试。
- ErrorInfo 的 message 和 details 必须脱敏并可 JSON 序列化。

错误码采用稳定分域格式：

```text
model.timeout
model.rate_limit
model.format
tool.validation
tool.permission
tool.execution
memory.storage
workflow.state
workflow.revision_mismatch
runtime.cancelled
runtime.internal
```

具体 ErrorCode 清单和捕获层级仍由对应 B-G 任务确认。

## 9. 已确认的 State 类型规则

State 表示一个可继续执行组件的当前可恢复快照。第一阶段最主要的公开 State 是 WorkflowState，不创建万能 `KernelState`。

必须保持：

```text
WorkflowState != WorkflowDefinition
WorkflowState != WorkflowInput
WorkflowState != Memory
WorkflowState != RunContext
WorkflowState != Events
```

State 使用严格、不可变的 Pydantic Schema。每次状态推进创建新实例：

```text
state_v1
  -> 执行 step_1
state_v2
  -> 执行 step_2
state_v3
  -> paused
```

状态转换必须重新执行 Schema 和业务不变量校验，不能依赖可能绕过完整校验的复制更新。

State 允许包含：

- 标量和 str Enum。
- UTC datetime。
- 冻结嵌套 Schema。
- tuple 等稳定集合。
- 受约束的 JsonValue。
- DefinitionRef。
- 已完成步骤的结构化结果或引用。

State 禁止包含：

- Model、Tool、Protocol 或 callable。
- asyncio Task、Lock、Event 或 Cancellation Token。
- 数据库连接和 Provider SDK 对象。
- Exception 和 Runtime 内存引用。

每种 State 必须通过：

```text
State
  -> model_dump_json()
  -> model_validate_json()
  -> 语义等价 State
```

Definition 与 State 使用两个独立版本：

```text
definition_ref.revision -> Definition 步骤和拓扑版本
state_schema_version    -> State JSON 结构版本
```

未知 revision 或 schema version 不自动迁移，必须返回明确错误。

checkpoint 与恢复授权分离：

```text
checkpoint_id -> 标识保存的 State，可以进入 State
resume_token  -> Runtime 的一次性恢复授权，不能进入 State
```

所有权：

| 模块 | 职责 |
|---|---|
| Workflow | 创建、解释和推进 WorkflowState |
| Runtime | 保存、取回、校验 resume_token 和驱动恢复 |
| State Store Adapter | 持久化和读取，不解释流程语义 |

Events 只作为审计证据，第一阶段不通过 Event Sourcing 恢复 Workflow。

resume_token 必须绑定 run_id、checkpoint_id 和 DefinitionRef；成功消费后立即失效，重复恢复不得重新执行已完成副作用。

具体 WorkflowState 字段和恢复协议仍由 G1、G4 确认。

## 10. 已确认的 JSON 与 metadata 公共边界

公共协议禁止使用 `Any`、`object` 和无类型 `dict` 绕过契约。

开放 JSON 数据只允许：

```python
JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]
```

这些别名描述 JSON wire shape，不表示 Kernel 可以长期保存外部传入的可变 list / dict 引用。

Schema 构造边界必须对开放 JSON 做防御性复制和规范化。State、Event 等不可变对象不能向调用方暴露可原地修改内部语义的引用。内存中的深度不可变表示必须能够稳定转换为标准 JSON；具体 Frozen JSON 容器实现由 A4 确认。

已知结构必须优先定义明确 Schema。JsonValue 只用于真正开放的数据：

- 尚未指定输出 Schema 的 Model 输出。
- Tool 通用执行包装。
- 受控 metadata。
- 脱敏 Provider 扩展信息。

metadata 不进入 KernelSchema 基类。只有确有扩展需要的具体对象才能声明 metadata，并且必须明确：

```text
谁写入
谁读取
是否参与核心逻辑
是否持久化
敏感数据规则
最大大小
```

metadata 按来源分域：

```text
metadata          -> Application 提供的安全扩展标签
runtime_metadata  -> Runtime 产生的运行信息
provider_metadata -> Adapter 白名单提取的 Provider 扩展信息
```

统一规则：

- Kernel 核心逻辑不能依赖 provider_metadata。
- Provider Adapter 禁止复制原始响应、请求头、凭证或 SDK 对象。
- Provider metadata 只能按白名单提取必要字段。
- datetime、Enum、UUID、Decimal 和 bytes 必须按字段契约显式转换。
- float 必须是有限值，禁止 NaN 和 Infinity。
- 哈希、幂等键、Checkpoint 完整性和证据比较必须使用 Canonical JSON。
- Canonical JSON 固定 UTF-8、key 排序、稳定分隔符、有限浮点、Enum value 和 UTC ISO 8601 datetime。
- 开放 JSON 必须限制嵌套深度、key 数、字符串长度和序列化字节数。
- 超限必须产生稳定 ErrorCode，不能截断后继续执行。

具体 Python 类型别名实现、Canonical JSON 工具和限制值由 A4 及首个使用任务确认。

## 11. A2 设计收口

A2 已逐项确认以下类型策略：

```text
Protocol / ABC
Definition
Input
Result
Event
Error
State
JsonValue / metadata
```

当前统一映射：

| 对象 | 类型策略 |
|---|---|
| 行为契约 | `typing.Protocol` |
| 共享实现 | 仅在确有复用时内部使用 ABC |
| Definition | frozen dataclass |
| Input / Result / Event / State | 严格 Pydantic Schema Model |
| Python 失败传播 | KernelError |
| 可序列化错误 | ErrorInfo |
| 状态和类型判别 | str Enum / Literal |
| 开放结构化数据 | 受约束 JsonValue / JsonObject |

A2 已完成逐项确认和任务级验收。本记录随 A2 原子提交合并回 `architecture`，后续具体字段只能由对应 B-G 任务在本策略边界内确认。
