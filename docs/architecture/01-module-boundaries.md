# 模块边界

本分册描述逻辑职责、依赖和 A3 已确认的物理边界。

## 六个核心原语

| 原语 | 拥有 | 不负责 |
|---|---|---|
| Runtime | run_id、生命周期、取消、暂停恢复验证、唯一终态 | Agent 推理、Workflow 流程语义、Provider 调用 |
| Agent | Instructions、ModelRequest 组装、Tool Call 循环、Memory 读取 scope 和写入目标决策 | Workflow 调度、Run 生命周期、Tool Backend |
| Workflow | 步骤拓扑、调度、分支、并行、流程位置、WorkflowState | 模型生成、恢复令牌校验、业务数据库 |
| Model | Provider Neutral 的 generate/stream 能力 | Prompt 所有权、Tool 执行、Memory 和业务规则 |
| Tool | 输入输出契约、一次 Backend 调用 | 自然语言推理、Workflow 路由、是否继续调用 Model |
| Memory | scope 分区隔离、存储、读取、搜索和序列化 | 决定记忆内容、自动共享、WorkflowState、Checkpoint、Trace 和业务事实 |

## Execution 支撑协议

| 能力 | 所有者边界 |
|---|---|
| RunContext | Runtime 创建并向下传递运行身份、deadline、metadata 和 cancellation |
| Hooks | 观察或扩展生命周期，不接管执行所有权 |
| Guardrails | 在输入、Model 输出和 Tool 调用边界执行允许或拒绝 |
| Retry | 根据错误、幂等、策略、次数、deadline 和取消状态决定安全重试 |
| Cancellation | 从 Runtime 传播到 Model、Tool、Memory 和 Workflow 步骤 |
| Streaming | 转发真实增量和运行事件，不改写最终 Result 或 State |

## 单向依赖

```text
Interface -> Application / Composition Root -> Kernel Contracts
Adapter   -> Kernel Contracts
Kernel    -X-> Interface
Kernel    -X-> Application
Kernel    -X-> Provider SDK
Kernel    -X-> 具体存储或 Tool Backend
```

Application 可以持有具体 Adapter 并完成依赖注入；Core 只能依赖公共契约。Adapter 不能把 SDK 类型、配置对象或私有状态泄漏到 Core。

## Memory 所有权

```text
Application -> Memory Policy、主体身份、可授权 scope 上下文
Agent       -> 读取哪些 scope、写入哪个 scope、MemoryItem 内容与来源
Memory      -> 按显式 scope 存储、搜索、序列化和隔离
Runtime     -> run_id、生命周期和事件引用
```

同一个 Memory Adapter 可以服务多个会话、用户和项目，但共享 Adapter 实例不代表
共享数据可见性。每次 read、search 和 write 都必须落在明确 scope 内。

当前确认的 scope 语义为：

| scope | 所属边界 | 默认共享规则 |
|---|---|---|
| 会话级 | 单个 Session | 不跨会话共享 |
| 用户级 | 单个用户主体 | 只向该用户的授权会话共享 |
| 项目 / 共享级 | 项目或授权成员集合 | 只向满足项目身份与权限的调用共享 |

禁止隐式跨 scope 读取。把会话级 Memory 提升到用户级或项目级时，Agent 必须在目标
scope 创建新的带来源 MemoryItem，不能移动原记录或由 Adapter 自动扩大可见范围。

## 数据所有权

```text
Definition -> 组件如何装配
Input      -> 本次调用收到什么
RunContext -> 本次 Run 的执行上下文
State      -> 可恢复组件当前在哪里
Event      -> 执行过程中已经发生什么
Result     -> 本次调用最终得到什么
Memory     -> 按 scope 隔离、可跨 Run 召回的上下文
```

这些对象不能通过万能基类或无类型 payload 合并。具体字段由对应 B-G 任务确认。

## 物理目录门禁

A3 已确认以下物理边界，A4 起按此建立工程：

- Kernel 正式包名为 `agent_kernel`，采用 `src/agent_kernel`。
- Adapter、Application 和 Interface 使用独立顶层命名空间。
- 不根据旧项目恢复模块布局。
- 不用计划文档反向决定模块归属。

A4 和后续实现不得创建平行 `core/`、`kernel/` 包，也不得改变公开导入路径而不更新规格和架构记录。
