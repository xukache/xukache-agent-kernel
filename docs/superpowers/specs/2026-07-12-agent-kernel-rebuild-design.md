# Agent Kernel 重构设计记录

> 状态：六个 Core 原语、Execution 执行层、支撑协议、Applications 和 Interfaces 已确认；全章已按参考规格细化，进入 v0.16 规格审查。
>
> 架构主分支：`architecture`
>
> 基线：新 Kernel 重构起点

本记录对应当前完整规格 `DEV_SPEC v0.16`。第 1-10 章的结构和内容已完成细化，当前仍待用户审查，不代表已经进入代码实现。

## 目标

从空白起点建立一个简洁、通用、可组合的 Agent Kernel。第一阶段只稳定通用内核，不引入业务、不兼容旧项目、不迁移旧代码。

## 已确认原则

1. 通用内核与业务应用完全分离。
2. 核心只保留少量稳定原语，不为每个阶段、能力或状态再创造一套平行名词。
3. Agent、Workflow、Tool、Memory、Model、Runtime 是第一阶段的核心原语。
4. 工伤认定、政策检索、待遇测算等全部属于后续业务层。
5. 旧项目的代码、文档、计划和协议不作为新 Kernel 的设计来源。
6. 任何第三方运行时只能作为 Runtime Adapter，不能进入核心协议。

## 核心原语

| 原语 | 唯一职责 |
|---|---|
| `Agent` | 使用 Model、Instructions、Tools 和 Memory 完成一次智能任务 |
| `Workflow` | 组合 Agent、Tool 和函数步骤，负责顺序、分支、并行、重试和暂停恢复 |
| `Tool` | 对外部能力提供结构化输入、结构化输出和受治理执行 |
| `Memory` | 读取和写入可持久化上下文，不负责业务路由 |
| `Model` | 提供模型生成能力，不负责业务规则和状态持久化 |
| `Runtime` | 执行 Agent 或 Workflow 生命周期，不负责业务语义 |

## 依赖关系

```text
Runtime
  -> Workflow
      -> Agent
          -> Model
          -> Tool
          -> Memory
      -> Tool
      -> Memory
```

跨模块事件、错误和运行上下文属于内核基础协议，但不单独扩展为新的业务对象体系。

## 目标目录

```text
src/
  agent_kernel/
    core/
      agent/
      workflow/
      tool/
      memory/
      model/
      runtime/
    adapters/
      runtime/
      model/
      memory/
      observability/
  applications/
  interfaces/
```

`applications/` 第一阶段保持为空，不提前放入业务模块。

## 核心禁止项

`core/` 不得依赖：

- 任何具体业务词汇。
- 任何具体 Provider SDK 或运行时框架。
- CLI、TUI、HTTP 等接口实现。
- 旧项目的聚合协议和数据模型。
- 具体存储格式或模型供应商实现。

## 模块 1 验收标准

- 可以只阅读 `core/` 解释 Agent Kernel，不需要了解工伤业务。
- 核心原语之间只有明确依赖，不出现无法归属的平行核心概念。
- 后续业务应用只能通过组合 Agent、Workflow、Tool、Memory 和 Model 接入。
- Runtime Adapter 可以替换，不改变核心原语的公共协议。

## Execution 执行层确认

状态：已确认。

```text
Retry 负责可安全重试的临时失败。
Cancellation 负责主动停止当前运行。
Streaming 负责逐步返回运行过程和输出。
Context、Hooks、Guardrails 只作为运行支撑能力存在。
```

## Agent 模块确认

状态：已确认。

```text
Agent 是独立的智能执行单元。
Agent 组合 Instructions、Model、Tools 和 Memory。
Agent 不负责 Workflow 调度、存储、UI、业务状态或运行生命周期。
Agent 由 Runtime / Execution 调用和治理。
```

## Tool 模块确认

状态：已确认。

```text
Tool 是明确、结构化、可治理的外部动作。
Tool 负责输入校验、外部执行、结构化输出和明确错误。
Tool 不负责推理、Workflow 路由、Prompt、共享状态或业务流程。
权限、超时、取消、幂等和 Trace 由 Execution 治理。
```

## Workflow 模块确认

状态：已确认。

```text
Workflow 是确定性的流程组合单元。
Workflow 连接 Agent、Tool 和函数步骤。
Workflow 负责顺序、分支、暂停、恢复和流程结果。
Workflow 不替代 Agent，不实现 Tool，不管理 Memory 存储或业务状态。
```

## Memory 模块确认

状态：已确认。

```text
Memory 负责跨运行保存和读取 Agent 上下文。
对话记忆、工作记忆和语义检索记忆属于 Memory 的使用方式。
Memory 不负责 Workflow 状态、Trace、UI 历史或业务数据库。
Memory 通过 Adapter 连接具体存储。
```

## Model 模块确认

状态：已确认。

```text
Model 是与具体 Provider 无关的模型调用能力。
Model 负责请求、响应、Tool Call 意图、usage 和模型错误。
Model 不负责 Prompt、Memory、Tool 执行、Workflow 路由或业务规则。
Agent 只依赖 Model 协议，不依赖具体 Provider SDK。
```

## Runtime 模块确认

状态：已确认。

```text
Runtime 负责 Agent / Workflow 的完整运行生命周期。
Runtime 协调 Execution，处理开始、执行、暂停、恢复、取消和结束。
Runtime 不负责 Agent 推理、Workflow 业务流程、Tool 实现或 Memory 存储。
具体 Runtime 只能通过 Adapter 接入，不能泄漏框架状态。
```

## 支撑协议确认

状态：已确认。

```text
Context 只描述当前运行。
Events 只描述运行过程。
Errors 统一失败和终止语义。
Agent、Tool、Workflow、Runtime 分别定义自己的结构化结果。
不创建万能结果对象或新的核心原语。
```

## Applications 业务组合层确认

状态：已确认。

```text
Application 负责组合 Kernel 能力完成具体业务。
业务 Prompt、规则、数据模型、业务 Tool 和业务 Workflow 都属于 Application。
Application 不修改 Kernel，不反向污染 Core，不复制一套框架。
Interface 只能通过 Application 使用业务能力。
```

## 对抗性审查修订摘要

对照参考项目的 `DEV_SPEC.md` 结构审查后，原规格被判定为 `REVISE`，主要缺口及修复如下：

| 审查缺口 | 修复 |
|---|---|
| 根规格版本号与入口不一致 | 统一为 `DEV_SPEC v0.15`，并补充版本索引 |
| Prompt 所有权不清晰 | 明确由 Application 提供模板和 Instructions，Agent 组装 Model Request，Execution 提供运行约束，Model 只负责生成 |
| Observability、Evals、Security、Integrations、RAG、Deployment 等外围能力悬空 | 增加外围能力归属表，明确不把它们扩张成 Core 原语 |
| 缺少跨模块最小契约 | 增加 `Core Contract Matrix`，明确输入、输出、错误、生命周期和替换点 |
| 缺少可落地的端到端路径 | 固定第一条纵向切片：Programmatic Interface、Application Fixture、单进程 Runtime、真实 Model Provider Adapter、In-memory Memory、无副作用 Tool 和 Events |
| 测试方案只有分类，没有证据口径 | 增加 `K-001` 至 `K-010` 验收矩阵，要求每个任务关联验收 ID 和证据 |
| 排期不可直接执行 | 增加 `K-01` 至 `K-07` 任务、依赖、输出和验收关系 |
| 每个模块拆成独立版本导致文档膨胀 | 同一设计里程碑合并为一个 `v0.15-kernel-design-baseline.md` |
| Workflow、Runtime、Memory 的边界仍偏描述性 | 补充流程状态、运行生命周期、跨运行上下文、暂停恢复、取消、错误和幂等验收要求 |

参考文档属于 RAG / MCP 应用项目。Chunk、Embedding、MCP、Dashboard 等技术不直接迁入 Kernel，而是归入 Application、Adapter、Interface 或 Product 层。

## 真实模型测试决策

用户已明确否决模拟模型。第一条纵向切片必须调用真实模型，当前通过 `ANANHU_REAL_MODEL` 选择模型，配置值为 `doubao-seed-2-0-mini-260428`。

测试规则：

```text
真实 Model Provider Adapter
  -> Agent
      -> Tool Call
      -> Memory
      -> Streaming Events
      -> Runtime Result
```

- 真实模型调用是 Agent、Model、Tool Call、Streaming 和纵向切片的必选验收路径。
- Provider 凭证、网络或模型配置不可用时，测试必须失败或明确阻塞，不得切换到模拟模型。
- 断言结构化输出、Tool Call、事件顺序、usage、错误和取消传播，不依赖固定自然语言全文。
- `ANANHU_REAL_MODEL_SMOKE=1` 才执行真实网络测试，结果记录模型标识、usage、延迟和错误分类。

## Interfaces 接口层确认

状态：已确认。

```text
Interface 是用户或外部系统访问 Application 的入口。
Interface 负责输入转换、Application 调用、事件转发、结果序列化和错误映射。
Interface 不负责 Agent、Workflow、Tool、Memory、Model 或业务规则。
Interface 不能绕过 Application 直接拼装 Kernel。
```

## 全章规格结构修订记录

本次修订将实现路径收敛为：

```text
Core 协议
  -> 真实 Model Smoke
  -> 真实 Agent 闭环
  -> Runtime / Execution / Workflow 控制
  -> Contract / Integration / Architecture Tests
  -> 第一个架构版本
  -> 业务 Application
  -> Interface
```

关键调整：

- 第 1 章增加项目目标、非目标、完成定义和设计原则。
- 第 2 章增加能力验收视图和关键取舍。
- 第 3 章按 Runtime、Adapter、Execution、配置、观测和真实模型拆分技术选型。
- 第 4 章按 TDD、Unit、Contract、Architecture、Integration、Real Model、E2E、Eval 和 CI/CD 拆分测试。
- 第 5 章按架构图、目录、Core 模块、执行流程、配置、扩展和纵向切片展开。
- 第 6 章按排期原则、阶段总览、A-H 进度跟踪和门禁展开。
- 第 7 章补充 Application、Provider、Interface、Observability、Evals 和生产化演进路径。
- 第 8-10 章补充模块确认模板、实现准入、阅读顺序和版本索引。
- 第一条纵向切片继续使用 `tests/integration/real_model_fixture`，真实 Model Smoke 前置，真实 Agent 闭环通过前不建立业务 Application。
