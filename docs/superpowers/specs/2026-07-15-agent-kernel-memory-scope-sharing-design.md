# Agent Kernel Memory scope、隔离与跨会话共享设计确认

## 1. 版本信息

| 字段 | 内容 |
|---|---|
| 日期 | 2026-07-15 |
| 状态 | 已确认，等待 E1-E6 实现 |
| 对应开发规格 | DEV_SPEC v0.26 |
| 对应架构版本 | v0.1-memory-scope-sharing |
| 实现状态 | Memory Core 尚未实现 |

## 2. 设计问题

此前文档只说明 Memory 按 `scope` 读写，但没有回答：

- 一个会话是否对应一个独立 Memory 实例。
- scope 如何区分会话、用户和项目。
- 为什么会话之间默认隔离。
- 同一用户的多个会话如何共享长期记忆。
- 会话记忆如何提升为用户级或项目级记忆。
- Memory 与 Session、WorkflowState、Checkpoint 的边界。

如果这些问题留到 Adapter 实现时临时决定，存储结构、权限检查、Agent Policy 和测试
会形成不同事实源，因此本次先冻结语义边界，不提前冻结 Python 字段。

## 3. 核心决策

### 3.1 一个 Memory 能力，多个 scope 分区

Memory 是可被多个 Agent、会话和用户共享装配的统一 Protocol。共享同一个 Adapter
实例只代表复用存储能力，不代表不同主体可以互相读取数据。

每次 `read`、`search` 和 `write` 都必须携带明确 scope。Application 和 Agent Policy
先确定授权范围，Adapter 再以 scope 作为分区边界，不允许从调用上下文或内容相似度
猜测可见范围。

### 3.2 三类 scope 语义

| scope | 典型内容 | 默认可见范围 |
|---|---|---|
| 会话级 | 当前任务上下文、临时偏好、中间结论 | 当前 Session |
| 用户级 | 跨会话稳定偏好、经确认事实、长期画像 | 同一用户的授权 Session |
| 项目 / 共享级 | 项目约定、团队共识、授权共享结论 | 被授权项目或成员集合 |

具体字段名、复合键和类型由 E1 确认。第一阶段只要求这些语义能够被稳定表达和测试。

### 3.3 会话默认隔离

会话隔离用于保证：

- 不同任务的临时结论不会互相污染。
- 同一用户并行会话可以采用不同上下文和假设。
- 敏感会话不会因为复用 Adapter 自动暴露。
- 召回结果、删除范围和错误定位保持可预测。
- 权限遵循最小可见原则。

因此，会话 B 不得直接读取会话 A 的会话级 scope，即使两个会话属于同一用户。

### 3.4 跨会话共享

跨会话共享通过用户级或项目级 scope 完成，不通过关闭会话隔离完成。

```text
会话 A 产生候选信息
  -> Agent 根据 Memory Policy 判断是否可复用
  -> 在用户级或项目级 scope 创建新的 MemoryItem
  -> 新条目保留 run、session 或原 MemoryItem 来源
  -> 会话 B 的 Policy 显式允许读取目标 scope
  -> Memory Adapter 在授权边界内返回结果
```

提升必须创建新条目，不能修改或移动原会话级条目。原始事实和共享事实需要能够独立
审计、撤销、过期和删除。

### 3.5 Memory Policy 所有权

```text
Application -> 配置 Policy，提供主体身份和可授权 scope
Agent       -> 决定何时读、读哪些 scope、写什么和写入哪里
Memory      -> 存储、搜索、序列化和 scope 隔离
Runtime     -> run_id、生命周期和事件引用
```

Memory Policy 至少需要表达：

- 允许读取的 scope 集合。
- 默认写入目标和允许提升的目标。
- 相关性排序、去重和上下文预算。
- 用户、项目或租户授权规则。
- 过期、删除、敏感信息和冲突处理。

Policy 的最终类型分别由 E1、E4 和 E5 确认。

## 4. MemoryItem 边界

MemoryItem 保存系统决定留下来的可复用信息，至少具有：

- 提炼后的内容。
- 来源引用。
- 创建时间。
- 可选元数据。

默认不保存完整聊天历史。来源应能追溯到 run、session 或前序 MemoryItem。

Memory 不保存：

- WorkflowState。
- Checkpoint。
- Trace 和 UI 历史。
- 完整 Tool Call 历史。
- 业务数据库事实。

当前 `ModelMemoryItem` 只是进入 ModelRequest 的只读投影，不代表 E1 的最终
MemoryItem 或 scope 数据模型已经实现。

## 5. Session、Memory、State 与 Checkpoint

| 概念 | 作用 | 所有者 |
|---|---|---|
| Session | 组织一段多轮交互并提供会话身份 | Application / Interface |
| Durable Memory | 保存按 scope 隔离、跨 Run 可召回的信息 | Memory |
| WorkflowState | 保存流程位置和步骤结果 | Workflow |
| Checkpoint | 保存可恢复运行快照 | Runtime |

Session 可以映射到会话级 scope，但 Session 本身不是 Memory Store。恢复执行不能只靠
重新读取聊天历史，WorkflowState 和 Checkpoint 也不能写入 Memory 代替恢复协议。

## 6. 第一阶段实现边界

- E1-E6 状态保持待开始。
- 第一阶段使用 In-memory Memory Adapter。
- 不提前引入数据库、向量数据库、Embedding 或语义检索引擎。
- 不自动把运行结果提升为长期可信 Memory。
- 不在本次文档任务中创建 `agent_kernel.memory` 实现文件。

## 7. 验收变化

K-006 和 RD-004 需要同时证明：

- 同一会话级 scope 可以召回。
- 另一个会话不能直接读取前一会话的会话级 Memory。
- 显式创建用户级 MemoryItem 后，同一用户的授权会话可以召回。
- 其他用户或未授权项目不可见。
- 跨 scope 提升创建新条目并保留来源链。
- 共享 Adapter 实例不会破坏隔离。

## 8. 关联文档

- [当前完整开发规格](../../../DEV_SPEC.md)
- [DEV_SPEC v0.26 增量](../../dev-spec/versions/v0.26-memory-scope-sharing.md)
- [完整架构版本 v0.1](../../architecture/versions/v0.1-memory-scope-sharing.md)
- [Memory 运行数据流](../../architecture/02-runtime-data-flow.md)
- [公共契约](../../architecture/03-public-contracts.md)

## 9. 已知限制

- scope 的最终 Python 字段、ID 类型和复合键尚未确认。
- Permission 的错误码和授权接口尚未确认。
- MemoryItem 的过期、删除和冲突解决字段尚未确认。
- 多 scope 排序、去重和预算算法尚未确认。
- 持久化、索引和语义检索实现不在第一阶段。
