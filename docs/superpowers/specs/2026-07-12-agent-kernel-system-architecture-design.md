# Agent Kernel 第五章系统架构与模块设计确认

> 日期：2026-07-12
>
> 状态：语义决策继续有效；章节表达已由 DEV_SPEC v0.23 重构
>
> 对应开发规格：DEV_SPEC v0.22，后续表达版本为 DEV_SPEC v0.23

## 1. 章节职责

第五章回答：

> Kernel 由哪些稳定模块组成，它们如何依赖、如何在一次运行中协作，以及每种数据和状态究竟由谁拥有？

本章不负责选择具体 Python 类型库或提前决定物理目录。

## 2. 方案选择

已确认采用方案 A：静态架构和运行时架构分别表达。

```text
静态架构
  -> 模块
  -> 依赖方向
  -> Adapter 替换点

运行时架构
  -> 调用顺序
  -> 状态变化
  -> 暂停恢复
  -> 结果和事件
```

两张图描述同一系统，但不能用运行调用反推代码依赖，也不能用静态分层代替执行流程。

## 3. Definition 与 Input

已确认：

```text
AgentDefinition != AgentInput
WorkflowDefinition != WorkflowInput
```

- AgentDefinition 持有 Instructions、Model、Tools、Memory 使用配置和执行上限。
- AgentInput 只描述本次任务、Memory scope 和调用元数据。
- WorkflowDefinition 持有 Steps、依赖、分支和暂停点。
- WorkflowInput 只描述本次流程的初始数据和调用元数据。

Definition 由 Application 或测试组合根创建，在运行中只读；Input 每次调用单独创建。

## 4. Memory 所有权

已确认：

```text
Application -> 配置 Agent 如何使用 Memory
Agent       -> 决定读取和写入时机，创建 MemoryItem
Memory      -> 存储、读取、搜索和 scope 隔离
Runtime     -> 提供 run_id、生命周期和事件引用
```

Memory 不主动决定写入内容，也不保存 WorkflowState、Trace、UI 历史或业务数据库事实。

## 5. 暂停恢复所有权

已确认：

```text
Workflow -> WorkflowState 和流程位置
Runtime  -> Run 生命周期、恢复校验和 resume_token
```

`resume_token` 不进入 `WorkflowState`。Runtime 先验证恢复请求，再把对应状态交给 Workflow。Workflow 通过已完成步骤和幂等键保证恢复后不重复副作用。

## 6. 公共契约范围

已确认六个 Core 都必须有独立语义契约：

| Core | 最小公共语义 |
|---|---|
| Agent | Definition、Input、执行、AgentResult、错误和非职责 |
| Workflow | Definition、Input、WorkflowState、WorkflowResult、错误和非职责 |
| Tool | 声明、ToolInput、执行、ToolResult、治理语义 |
| Memory | read、write、search、MemoryItem、scope 和存储错误 |
| Model | ModelRequest、generate / stream、ModelResponse 和 Provider 错误 |
| Runtime | RunRequest、run / resume / cancel、RuntimeResult、事件和生命周期 |

本次确认的是语义，不是最终 Python 方法签名。

## 7. 物理目录决策

旧的扁平 Core 布局和 `core` 嵌套布局都不再有效，也不再保留具体路径示例，避免被误认为实现事实。

目录需要在首个模块实现前单独展示，必须能表达：

- Core 公开 API。
- Definition、Input、Result 和支撑协议的归属。
- Adapter 和参考实现的关系。
- Contract、Integration、Architecture 和 RD 测试组织。
- 单向导入规则。

在用户确认目录前不得创建 Kernel 代码目录。

## 8. 边界

本次确认不改变：

- 六个核心原语。
- Application 和 Interface 的外层边界。
- K/RD 测试范围。
- 真实 Provider 验收要求。
- 旧项目不兼容、不读取、不迁移规则。

仍待确认：

- Python 公共类型表达。
- 物理目录和公开导入路径。
- 具体 Provider SDK、Schema 库和 Adapter 配置。
- 首个完整架构版本正文的创建时点。

本次确认完成第五章设计，不代表第六章及后续章节已经通过本轮逐章审查，也不授权开始代码实现。
