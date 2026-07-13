# 模块边界

本分册只描述逻辑职责和依赖，不提前决定 A3 的物理目录。

## 六个核心原语

| 原语 | 拥有 | 不负责 |
|---|---|---|
| Runtime | run_id、生命周期、取消、暂停恢复验证、唯一终态 | Agent 推理、Workflow 流程语义、Provider 调用 |
| Agent | Instructions、ModelRequest 组装、Tool Call 循环、Memory 读写决策 | Workflow 调度、Run 生命周期、Tool Backend |
| Workflow | 步骤拓扑、调度、分支、并行、流程位置、WorkflowState | 模型生成、恢复令牌校验、业务数据库 |
| Model | Provider Neutral 的 generate/stream 能力 | Prompt 所有权、Tool 执行、Memory 和业务规则 |
| Tool | 输入输出契约、一次 Backend 调用 | 自然语言推理、Workflow 路由、是否继续调用 Model |
| Memory | scope 隔离、存储、读取和搜索 | 决定记忆内容、WorkflowState、Trace 和业务事实 |

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

## 数据所有权

```text
Definition -> 组件如何装配
Input      -> 本次调用收到什么
RunContext -> 本次 Run 的执行上下文
State      -> 可恢复组件当前在哪里
Event      -> 执行过程中已经发生什么
Result     -> 本次调用最终得到什么
Memory     -> 跨 Run 可召回的上下文
```

这些对象不能通过万能基类或无类型 payload 合并。具体字段由对应 B-G 任务确认。

## 物理目录门禁

A3 完成前禁止：

- 创建 Kernel 代码目录。
- 声明正式 Python 包名或公开导入路径。
- 根据旧项目恢复模块布局。
- 用计划文档反向决定模块归属。

A3 必须基于六个 Core 的公开 API、Definition/Input/Result 归属、Adapter 导入方向和测试组织单独确认。
