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

完整规则和示例以 A2 确认记录为准；具体字段、枚举和错误捕获层级由 B-G 对应任务确认。
