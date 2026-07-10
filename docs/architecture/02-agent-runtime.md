# 02. Agent 运行时架构

## 范围

本文定义运行时所有权、框架中立状态、LangGraph 边界、Agent 协议、状态合并、重试和恢复。

## 当前与目标运行时

```text
WorkflowRuntime
  +-- NativeWorkflowRuntime      显式回归运行时
  +-- LangGraphWorkflowRuntime   当前默认运行时
```

当前 `LangGraphWorkflowRuntime` 是默认运行时，使用 LangGraph 串行调度项目阶段；业务状态仍只通过项目 reducer 合并。通过 `RuntimeSettings(runtime="native")` 可显式切回 `NativeWorkflowRuntime` 做回归。CLI、Eval 和后续外部入口只依赖 `WorkflowRuntime` 端口。

## 运行时所有权

- 选定的 `WorkflowRuntime` 拥有节点调度、条件路由、中断和终止权。
- 项目 `TransitionPolicy` 和 reducer 拥有业务状态合并语义。
- Agent 和阶段服务只返回结构化结果或 `StatePatch`。
- Repository 拥有业务记录持久化，checkpointer 只拥有运行时恢复数据。

## 框架中立协议

```text
RunRequest       不可变请求、身份关联和可信 jurisdiction
WorkflowState    可序列化的单次 run 业务状态
StatePatch       阶段产生的显式增量
WorkflowResult   完成、追问、拒答或失败结果
StopReason       框架无关停止语义
```

`WorkflowState` 至少包含：

- `schema_version`、`run_id`、`request_id`、`session_id`、`case_id`。
- `phase`、`status`、`stop_reason`、`attempt_count`、`capability_call_count`。
- 案件事实、意图结果、执行计划、能力结果和证据。
- 答复草稿、验证结果和安全结果。

禁止将运行时内部临时上下文注册为 LangGraph State。LangGraph 只能通过 adapter 投影项目 `WorkflowState`。

`ananhu_agent/workflow/contracts.py` 已落地首版框架中立协议：

- `RunRequest`：承载 `request_id`、`run_id`、`session_id`、`case_id`、`message_id`、可信 jurisdiction 和不可变用户输入。
- `WorkflowState`：承载单次 run 的可序列化业务状态投影。
- `WorkflowResult`：承载完成、追问、证据不足、能力失败和安全拦截等停止结果。
- `WorkflowPhase`、`RunStatus`、`StopReason`：冻结 Native 与后续 LangGraph Runtime 共享的阶段、状态和停止语义。
- `WorkflowRuntime.invoke()`：async 运行时端口，CLI、EvalRunner 和后续入口通过该端口调用运行时。

默认组合根为 `create_default_runtime()`，按 `RuntimeSettings.runtime` 装配运行时，默认值为 `langgraph`；`native` 是保留的显式回归选项。

## StatePatch 与 Reducer

每个阶段返回自己拥有字段的增量，禁止原地修改共享列表或字典：

```text
StatePatch
  patch_id
  run_id
  source_phase
  node_id
  logical_call_id
  attempt
  fact_updates
  intent_result
  execution_plan
  capability_results
  evidence
  draft_final_answer
  verification_result
  safety_result
  final_answer
  next_phase
  status
  stop_reason
```

当前 reducer 已在 `ananhu_agent/workflow/reducer.py` 以普通 Python 纯函数实现并独立测试，不依赖 LangGraph reducer 类型。合并规则为：

- `patch_id` 去重：重复 patch 不重复追加列表字段。
- `phase` 校验：非法跳转返回结构化失败，不抛框架异常。
- `fact_updates` 按字段覆盖写入 `case_facts`。
- `intent_result`、`execution_plan`、答复、校验、安全和终止字段为显式覆盖。
- `capability_results` 按 `tool_call_id` 合并。
- `evidence` 按 `evidence_id` 合并。

## LangGraph 边界

LangGraph可以负责：

- StateGraph 节点和条件边。
- 单次 run 的调度、interrupt、resume 和节点重试。
- 共享同一事实版本的有限并行。
- 调用项目 checkpointer port 的适配实现。

LangGraph不得定义：

- 案件事实、Evidence、Capability、Response 数据结构。
- 业务 reducer、路由规则、StopReason 和错误码。
- Tool 权限、幂等和重试语义。
- 项目 trace、usage 和 eval schema。

LangGraph专有类型只能存在于 `runtimes/langgraph/` 和组合根。Graph node 应保持薄：读取项目状态、调用 application service、返回项目 `StatePatch`。

## 稳定阶段与节点

首个 LangGraph 实现只映射串行业务阶段：

```text
understand
  -> merge_facts
  -> validate_facts
  -> clarify | resolve_jurisdiction
  -> plan
  -> execute
  -> validate_evidence
  -> compose
  -> safety
  -> complete
```

不要把四个 Agent 机械变成四个节点。Agent 是能力组织方式，节点是状态转换阶段。

## Native Runtime 阶段服务

`ananhu_agent/runtimes/native/` 提供阶段服务与 Native Runtime；`ananhu_agent/runtimes/langgraph/` 将同一阶段服务映射为串行图：

- 阶段服务读取 `WorkflowState`，返回 `StatePatch`。
- 两种 Runtime 都通过 `reduce_workflow_state()` 应用 patch，不让 CLI/Eval 原地操作大状态对象；LangGraph 节点只返回 patch，独立 `apply_patch` 节点负责调用 reducer。
- `execute` 阶段把 Agent 生成的工具意图转换为 `CapabilityRequest`，统一经过 `CapabilityGateway`，不绕过 ToolExecutor 治理。
- `TraceEvent` 统一写入实际 `runtime_name`、`node_id`、`logical_call_id` 和 `attempt`。
- `WorkflowResult.final_state` 仅作为 Eval 和诊断使用的状态快照，CLI 对外仍只展示最终答复、追问或错误信息。

## Agent 当前协议与目标规则

- 当前 Agent 无状态，读取运行时内部上下文并返回 `AgentMessage` / `ToolCallRequest`；Native 阶段服务负责转换为 `StatePatch` 和 `CapabilityRequest`。
- Native 阶段服务返回 `StatePatch`，并将工具调用转换为 `CapabilityRequest`；Agent 不直接写 session、case 或 WorkflowState。
- 当前和目标输入输出均使用项目 Pydantic/domain model，不使用框架 message。
- Agent 不能持有底层能力实现，也不能自行选择未经授权的 jurisdiction 或知识库。
- 新增 Agent 必须证明独立目标、上下文、权限或专项评测价值。

当前四 Agent 是 Native MVP 的内部实现。后续允许将 `PolicyRAGAgent`、`PaymentCalculationAgent` 收敛为应用服务或 Capability，但必须通过行为回归后再删除。

## 重试与幂等

模型重试、节点重试和能力重试必须分开计数。每次能力调用使用稳定的：

```text
run_id + node_id + logical_call_id + capability_version
```

`attempt` 记录物理尝试次数，不参与逻辑幂等键。重复执行前由 CapabilityGateway 根据幂等等级决定返回历史结果、重新执行或拒绝。

## 状态和恢复边界

| 对象 | 用途 | 是否权威业务事实 |
|---|---|---:|
| `CaseRecord` | 跨会话案件事实 | 是 |
| `SessionRecord` | 连续对话和工作记忆 | 否，需引用事实来源 |
| `RunSnapshot` | 当前运行审计投影 | 否 |
| `CheckpointEnvelope` | 运行时恢复 | 否 |
| `TraceEvent` | 过程审计 | 否，不直接用于恢复 |

checkpoint 必须带状态 schema、runtime、Prompt、Tool Registry、知识语料版本。恢复前检查兼容性；不能安全迁移时返回结构化失败，不能静默继续。

## 异步与流式边界

- application service、模型、检索和能力执行采用 async 边界。
- `WorkflowRuntime` 未来可同时提供 `invoke()` 和项目定义的 `stream()` 事件。
- 当前 CLI 可以消费最终结果；未来外部流式协议不能直接暴露 LangGraph 事件。
- 首个 LangGraph 实现不启用 ToolNode 直连、checkpoint、interrupt、复杂并行、后台队列或多路事件流。

## Contract Tests

Native 与 LangGraph Runtime 使用同一输入 fixture，至少断言：

- 最终 `WorkflowResult` 语义一致。
- 关键 phase 和 StopReason 一致。
- CapabilityRequest、权限和幂等语义一致。
- 项目 trace 必需事件完整。
- 追问、安全拦截和失败分类一致。
