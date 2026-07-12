# Agent Kernel 第五章架构表达重构确认

> 日期：2026-07-12
>
> 状态：已由用户确认并写入 DEV_SPEC v0.23
>
> 基线：DEV_SPEC v0.22

## 1. 问题

v0.22 的第五章把静态依赖与运行时调用分开，语义决策正确，但开头的图只表达：

```text
Interface -> Application -> Runtime -> Agent / Workflow
```

它缺少 Agent 内部循环、Workflow 调度、Adapter 连接、外部系统和证据出口，因此只能作为依赖草图，不能承担“整体架构图”的职责。

## 2. 参考文档的有效方法

参考文档的优势不在于图大，而在于：

- 第一张图覆盖系统全貌。
- 每层内部继续展开关键模块。
- 抽象和具体实现放在同一条连接关系中。
- 主链路箭头连续。
- 后续章节再拆离线、在线和管理数据流。

本项目只借鉴表达方法，不迁入 MCP、RAG、Embedding、Vector Store 或 Dashboard 等业务组件。

## 3. 已确认重构

第五章采用以下阅读顺序：

```text
整体架构图
  -> 核心运行架构
  -> 模块说明
  -> 四条核心数据流
  -> Adapter 与配置
  -> 扩展性
  -> 状态所有权
  -> 物理目录状态
```

第一张图必须同时出现：

- 外部调用者。
- Interface 和 Composition Root。
- Runtime 和 Execution Governance。
- Agent Engine。
- Workflow Engine。
- Model、Tool、Memory Contracts。
- Adapter Layer。
- External Systems。
- Structured Evidence 和 Observability。

## 4. Agent Engine 表达

Agent 内部必须明确展示：

```text
Memory Read
  -> Model Request Builder
  -> Model
  -> Tool Call
  -> Tool Result 回传 Model
  -> Memory Write
  -> AgentResult
```

这条循环是学习 Agent 框架的核心，不能隐藏在一句“Runtime 调用 Agent”后面。

## 5. Workflow Engine 表达

Workflow 内部必须明确展示：

```text
WorkflowState
  -> Step Scheduler
      -> Agent Step
      -> Tool Step
      -> Function Step
      -> Branch / Parallel / Pause
  -> WorkflowResult 或 paused state
```

恢复请求仍由 Runtime 校验，Workflow 只从明确状态继续推进。

## 6. 数据流

第五章分别维护四条数据流：

| 数据流 | 需要解释 |
|---|---|
| Agent 执行流 | 输入、Memory、Model、结果和终态 |
| Tool Call 循环 | 模型意图、校验、执行、结果回传和循环终止 |
| Memory 读写流 | 策略、scope、来源、写入和隔离 |
| Workflow 执行与恢复流 | Step 推进、暂停、token 校验和幂等恢复 |

整体架构图负责“有什么”，数据流负责“怎么运行”。

## 7. 保留决策

v0.22 以下决策继续有效：

- Definition 与 Input 分离。
- Agent 决定 Memory 使用时机并创建 MemoryItem。
- Memory 负责存储和 scope 隔离。
- Workflow 拥有 WorkflowState。
- Runtime 拥有 Run 生命周期和 resume_token。
- 六个 Core 的语义级公共契约。
- 物理目录待单独确认。

## 8. 边界

本次只重构第五章的架构表达，不新增 Core，不选择具体 SDK，不创建物理目录，不授权代码实现。
