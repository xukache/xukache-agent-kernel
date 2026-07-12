# Agent Kernel 重构设计记录

> 状态：第一至七章主线、六个 Core 原语、Execution 支撑协议、Applications、Interfaces、渐进式真实对话验收和完整系统演进路线均已确认。
>
> 架构主分支：`architecture`
>
> 基线：新 Kernel 重构起点

本记录对应当前完整规格 `DEV_SPEC v0.25`。项目已确认以“通过实现理解 Agent 框架”为首要定位，以七项核心特点说明 Kernel 的工程作用和学习价值，明确核心机制自研、通用基础设施复用的技术边界，采用确定性测试与真实对话双轨验收，通过整体架构和四条数据流表达六个 Core 的协作关系，将第一阶段展开为 8 个阶段、47 个可执行任务，并明确从 Kernel 到 Agent Harness、业务 Application 和有证据支撑的 Multi-Agent 的后续演进路线。物理目录、Python 类型表达和 Provider 接入仍待实现准入阶段确认，不代表已经进入代码实现。

## 项目排期章节确认

状态：已确认。

第六章不再只保留阶段摘要表，而是让目录直接展示完整施工路径：

```text
规格与实现准入
  -> Model MVP
  -> Agent MVP
  -> Tool Call 闭环
  -> Memory 跨运行上下文
  -> Runtime 与 Execution
  -> Workflow 控制语义
  -> Kernel 累计验收与发布
```

共 47 个任务。每项任务统一说明学习问题、前置依赖、交付、验收和 K/RD 关联。旧 A1-A10 文档修订记录继续由 `docs/dev-spec/README.md` 的版本历史维护，不再作为实现任务。

## 系统架构章节确认

状态：已确认。

第五章首先提供能够看到系统全貌的整体架构图，再分层展开：

```text
整体架构图
  -> 核心运行架构
  -> 六个 Core 与 Execution 模块说明
  -> Agent / Tool Call / Memory / Workflow 四条数据流
  -> Adapter、扩展、所有权和目录状态
```

关键所有权：

```text
AgentDefinition != AgentInput
WorkflowDefinition != WorkflowInput

Agent 决定 Memory 的读取和写入时机，并创建 MemoryItem
Memory 负责存储、搜索和 scope 隔离

Workflow 拥有流程位置和 WorkflowState
Runtime 拥有 Run 生命周期、恢复校验和 resume_token
```

v0.22 确认的六个 Core 协议语义和所有权继续有效。v0.23 修复了原图只有依赖草图、看不到 Agent 循环、Workflow 调度、Adapter 连接和证据出口的问题。最终 Python 签名、类型工具和物理目录仍需逐模块确认。

## 测试与验收章节确认

状态：已确认。

```text
确定性测试：证明协议、边界、错误和状态转换
真实对话：证明模块在真实累计链路中承担职责
测试替身：只允许补充确定性条件
模块完成：当前 K/RD、历史 RD、架构边界和证据同时通过
```

第一阶段不把 Kernel 累计集成称为产品 E2E；Application E2E 在业务层建立后单独定义。

## 技术决策章节确认

状态：已确认。

```text
核心机制：自行设计和实现
通用基础设施：复用成熟工具
第一阶段：只选择打通真实链路所需的最小技术组合
具体 SDK 和 Schema 库：逐模块确认
模型标识：运行配置，不属于 Kernel 架构
```

第三章不再重复维护 Model、Workflow 和 Execution 的完整协议字段；相关事实统一归入第五章。

## 核心特点章节确认

状态：已确认。

第二章只保留以下七项能力概览：

```text
六个原语的最小心智模型
从输入到结果的完整执行闭环
组合式架构与单向依赖
Adapter 驱动的全链路可替换
结构化结果与可解释运行过程
渐进式真实对话验证
从通用 Kernel 扩展到业务 Application
```

六个模块的完整输入、输出、边界和验收继续由第五章维护；模块确认过程由 `docs/superpowers/specs/` 保存，第二章不再重复展开。

## 目标

通过从零设计和实现一个简洁、通用、可组合的 Agent Kernel，系统学习 Agent 框架的核心原理、模块边界和工程化方法。第一阶段只稳定通用内核，不引入业务、不兼容旧项目、不迁移旧代码。

## 学习定位确认

状态：已确认。

```text
首要目标：学习和理解 Agent 框架
实践方式：逐模块设计、实现并进行真实链路验证
最终成果：可复用的通用 Agent Kernel
```

项目不以阅读概念、拼装成熟框架或展示功能数量作为完成标准。学习结果必须通过设计文档、公共契约、可运行代码、自动化测试和累计真实对话证据共同体现。

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

用户已明确否决模拟模型。第一条纵向切片必须调用真实模型，模型通过 `ANANHU_REAL_MODEL` 运行配置选择；具体模型标识必须记录在测试证据中，但不作为 Kernel 架构常量。

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

## 渐进式真实对话验收确认

状态：已确认。

```text
每个模块实现任务完成时，都必须使用固定、可复核的真实用户对话输入。
真实输入必须经过当前已经完成的累计 Kernel 链路。
当前模块必须在链路中承担明确职能，并产生可校验输出、事件或状态变化。
模块完成时运行新增真实场景，同时回归此前全部真实场景。
Unit / Contract Test 继续保留，但不能单独证明模块实现完成。
主要完成证据不得使用模拟模型、固定模型输出或静默 fallback。
Fixture 不得预填 Tool 参数、Memory 内容、Workflow 分支、步骤结果或最终答案。
对应 Unit / Contract Test 必须随模块实现建立，最终阶段只做累计回归。
```

第一条真实链路不再等所有模块完成后一次组装，而是按以下顺序逐步增长：

```text
真实 Model
  -> Agent
  -> Tool
  -> Memory
  -> Runtime / Events / Execution
  -> Workflow
```

每一步都必须有真实对话输入、精确结构化断言和累计回归证据。具体场景以 `DEV_SPEC.md` 中的 `RD-001` 至 `RD-012` 为准。

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
- 第 5 章先展示系统全貌，再按核心运行结构、模块职责和四条数据流展开；保留 Definition/Input、Memory 和暂停恢复所有权，物理目录继续待确认。
- 第 6 章按排期原则、阶段总览、A-H 进度跟踪和门禁展开。
- 第 7 章说明从 Kernel 到 Agent Harness、业务 Application、Multi-Agent 和证据闭环的演进路线。
- 模块确认模板和实现准入迁移到 `docs/superpowers/specs/README.md`。
- 版本规则和历史迁移到 `docs/dev-spec/README.md`。
- 文档索引和阅读顺序迁移到根 `README.md`，`DEV_SPEC.md` 最终止于第七章。
- 第一条纵向切片继续使用累计真实对话 Fixture，具体测试路径待目录确认；真实 Model Smoke 前置，真实 Agent 闭环通过前不建立业务 Application。
