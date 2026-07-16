# 运行数据流

## Agent 执行流

```text
AgentInput
  -> Runtime 创建 RunContext
  -> Application 提供 scope 上下文
  -> Agent 按 Memory Policy 读取明确授权的 scopes
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

## Memory 读写与共享流

```text
Application 配置 Memory Policy
  -> Application 提供会话、用户和可选项目的 scope 上下文
  -> Agent 解析本次允许读取的 scope 集合
  -> Agent 分别发起 read / search
  -> Application / Agent Policy 完成授权检查
  -> Memory Adapter 对每个显式 scope 执行分区隔离
  -> Agent 对结果排序、去重并应用上下文预算
  -> 选中的 MemoryItems 进入 ModelRequest
  -> Agent 从运行结果创建带来源的 MemoryItem
  -> Agent 按 Policy 选择写入目标 scope
  -> Memory.write(target_scope, items)
  -> Event 记录 run_id、目标 scope 和来源引用
```

Agent 决定何时读取、读取哪些 scope、写什么和写入哪里；Memory 决定如何存储、
搜索、序列化和隔离。

跨会话共享使用以下链路：

```text
会话 A 的会话级 MemoryItem
  -> Agent / Application Policy 确认可以长期或共享复用
  -> 在用户级或项目级 scope 创建新的 MemoryItem
  -> 新条目保留原始 MemoryItem / run / session 来源
  -> 会话 B 仅在 Policy 明确允许读取目标 scope 时召回
```

不得直接读取另一个会话的会话级 scope，不得把“相似内容”当作跨权限召回依据，也
不得通过修改原条目 scope 完成静默提升。

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
