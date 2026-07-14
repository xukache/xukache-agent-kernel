# 运行数据流

## Agent 执行流

```text
AgentInput
  -> Runtime 创建 RunContext
  -> Agent 按 scope 读取 Memory
  -> Agent 组合 Instructions、Input、MemoryItems 和 Tool Schemas
  -> Model.generate / stream
  -> 处理 Tool Call 或构建 AgentResult
  -> Agent 按策略创建 MemoryItem
  -> Memory.write
  -> RuntimeResult + Terminal Event
```

Agent 的推理循环只属于当前 Run，不使用跨 Run 的共享可变状态。

## Function Calling 流

```text
Application 注入可执行 Tool 到 AgentDefinition
  -> Agent 提取 ToolDefinition / Tool Schema
  -> Model Adapter 转换为 Provider Schema
  -> Provider 返回 Tool Call
  -> Adapter 转换为 Kernel ToolCall
  -> Agent 检查白名单并按 name 找到 Tool
  -> ToolInput Schema 校验
  -> Guardrail / Permission / Cancellation / Idempotency
  -> Tool 调用 Backend
  -> Kernel ToolResult
  -> Agent 将 ToolResult 放入下一次 ModelRequest
  -> Model 返回最终回答、新 ToolCall 或达到执行上限
```

必须保持：

```text
Tool != ToolDefinition != ToolCall != ToolResult
Model 看见 Schema != Model 获得 Python callable
```

Model 只选择工具并生成参数；Agent 控制循环；Tool 只执行一次调用；Runtime / Execution 提供治理。

## Memory 读写流

```text
AgentInput.scope
  -> Agent 发起 read / search
  -> Memory Adapter 保证 scope 隔离
  -> MemoryItems 进入 ModelRequest
  -> Agent 从运行结果创建带来源的 MemoryItem
  -> Memory.write
  -> Event 记录 run_id、scope 和来源引用
```

Agent 决定何时读取和写什么，Memory 决定如何存储、搜索和隔离。

## Workflow 执行与恢复流

```text
WorkflowInput
  -> Runtime.run
  -> Workflow 创建 WorkflowState
  -> Step Scheduler 执行 Agent / Tool / Function / Branch / Parallel
  -> 保存 StepResult 和流程位置
  -> completed / failed
  -> 或 paused + WorkflowState

resume_input + resume_token
  -> Runtime 校验 token、Run、checkpoint 和终态
  -> Runtime 取回 WorkflowState
  -> Workflow 从明确位置继续
  -> 已完成副作用步骤不得重复
```

Workflow 拥有并解释 WorkflowState；Runtime 拥有恢复授权和一次性 `resume_token`；State Store Adapter 只负责持久化。

## 证据流

- Runtime 为同一 run 分配单调递增的 Event sequence。
- 每个 Tool Call 产生参数摘要、开始、完成或错误证据。
- 每个 Run 只能有一个 Terminal Event。
- Result 可以保存事件引用或摘要，不能复制完整 Events。
- WorkflowState 是恢复事实源，第一阶段不通过 Event Sourcing 恢复。
