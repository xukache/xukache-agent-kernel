# Agent Kernel Developer Specification

> 版本：0.16 — Agent Kernel 执行链路与实现排期基线
>
> 状态：设计完成，待用户审查；当前分支不继承旧项目事实源
>
> 当前架构主分支：`architecture`
>
> 文档目的：冻结当前完整设计、跨模块契约、验收口径和实现顺序；本文件不包含具体实现代码。

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 核心特点](#2-核心特点)
- [3. 技术选型](#3-技术选型)
- [4. 测试方案](#4-测试方案)
- [5. 系统架构与模块设计](#5-系统架构与模块设计)
- [6. 项目排期](#6-项目排期)
- [7. 可扩展性与未来展望](#7-可扩展性与未来展望)
- [8. 模块确认记录](#8-模块确认记录)
- [9. 开发规格维护与版本化](#9-开发规格维护与版本化)
- [10. 当前文档索引](#10-当前文档索引)

---

## 1. 项目概述

### 1.1 项目定位

本项目重建一个简洁、通用、可组合的 Agent Kernel。

Kernel 只提供 Agent 应用需要的稳定能力和执行边界，不包含工伤咨询、政策、赔偿、地区、Evidence 等业务概念。业务应用单独放在 `applications/` 中，通过组合 Kernel 能力完成具体任务。

### 1.2 为什么重建

当前系统在长期演进中把业务流程、状态协议、工具治理、提示词、运行时和接口能力放在了相互交织的位置，导致：

- 核心能力和工伤业务难以分离。
- 同一职责出现多个平行概念。
- 更换模型、运行时或存储时需要牵动业务代码。
- 新人需要同时理解基础设施和业务流程才能理解系统。

本次重建从空白 Kernel 起点开始。旧项目完整保留在 `mvp` 和 `main`，当前分支不读取、不兼容、不迁移旧代码、旧文档、旧计划或旧业务协议。

### 1.3 设计理念

#### 1.3.1 核心优先 (Core First)

先稳定通用 Agent 能力，再建立业务应用。第一阶段不迁移旧工伤业务，也不保留旧业务协议兼容层。

实施判断标准：

| 判断问题 | 必须满足的结果 |
|---|---|
| 能否脱离业务解释？ | 可以只阅读 Kernel 说明该能力 |
| 能否替换实现？ | 替换 Provider、存储或运行时不改业务协议 |
| 能否独立验收？ | 有独立输入、输出、错误和测试证据 |

#### 1.3.2 少量原语 (Minimal Primitives)

核心只保留六个原语：

```text
Agent
Workflow
Tool
Memory
Model
Runtime
```

其他内容只能作为支撑协议或实现细节存在，不能继续扩张成一套平行的核心名词体系。

新增名词前必须回答：

1. 该职责是否已经由六个 Core 原语表达。
2. 该名称是否只是实现细节或测试概念。
3. 新名称是否会改变依赖方向或状态边界。

无法证明必要性时，不新增。

#### 1.3.3 组合优于继承 (Composition over Inheritance)

Agent 组合 Model、Tool 和 Memory；Workflow 组合 Agent、Tool 和步骤；Application 组合 Kernel 能力完成业务。

组合规则：

```text
Application = 业务配置 + Kernel 原语组合
Workflow = Agent / Tool / Function Step 组合
Agent = Instructions + Model + Tool + Memory 组合
```

业务不通过继承修改 Kernel 行为。

#### 1.3.4 依赖方向单一 (One-Way Dependency)

Kernel 不依赖业务。业务、接口和适配器依赖 Kernel 的公开协议。

禁止方向：

```text
Kernel -X-> Application
Kernel -X-> Interface
Kernel -X-> Provider SDK
Core -X-> 具体存储
```

#### 1.3.5 真实效果优先 (Real-Model Validation)

模型相关验收必须通过真实 Model Provider：

- 不使用模拟模型、固定文本替身或静默降级。
- 真实模型调用记录模型标识、usage、延迟、事件和错误。
- 真实模型不可用时测试失败或阻塞，不伪造通过。

#### 1.3.6 文档即工程契约 (Specification as Contract)

每个设计决策必须同时说明：

```text
目标
边界
输入 / 输出
错误
验证方法
后续扩展
```

### 1.4 当前范围

本文件当前只覆盖：

- Kernel 的定位和设计原则。
- 六个核心原语的职责边界。
- Kernel、Adapter、Application、Interface 的层次关系。
- 跨模块支撑协议、最小公开契约和端到端运行链路。
- 可执行验收矩阵和第一条纵向实现切片。
- 逐模块确认、实现和验收的工作方式。
- 文档、测试和架构演进的组织方式。

本文件当前不覆盖：

- 工伤认定、劳动能力鉴定和待遇测算。
- 政策检索和业务知识库。
- 具体模型供应商和 Prompt 内容。
- CLI、TUI、HTTP API 的具体实现。
- 具体代码目录内部实现。

#### 1.4.1 当前交付目标

本阶段完成后必须得到：

| 目标 | 可观察结果 |
|---|---|
| Kernel 可运行 | 真实 Model、Agent、Tool、Memory、Runtime 闭环可执行 |
| Kernel 可替换 | Model、Memory、Tool、Runtime Adapter 可替换 |
| Kernel 可解释 | Events、Result、usage 和错误可追踪 |
| Kernel 可测试 | Contract、Integration、Architecture Tests 可重复执行 |
| Kernel 可扩展 | 业务只通过 Application 组合，不修改 Core |

#### 1.4.2 明确非目标

以下内容不属于当前 Kernel 基线：

- 工伤业务规则和业务数据模型。
- RAG、MCP、向量数据库和知识库实现。
- 生产级多租户、分布式调度和远程 Runtime。
- 完整 CLI、TUI、HTTP 或 Web Dashboard。
- 以“多 Agent 数量”作为展示目标。

### 1.5 新项目清理策略

本分支只保留新 Kernel 重构所需的规格、确认记录和文档规则。旧项目中的以下内容全部删除：

- 旧 Python 包和业务代码。
- 旧测试、数据、模型配置和运行产物。
- 旧 CLI、TUI、Runtime、Tool、Prompt、Storage 和 Evaluation 实现。
- 旧架构正文、旧 API 契约、旧后端规范和旧计划。
- 旧模块确认文档中不适用于新 Kernel 的内容。

删除只发生在当前重构分支；`mvp` 和 `main` 继续作为旧项目的完整保留版本。

### 1.6 设计结果

最终要得到的不是一个“工伤 Agent 的重命名版本”，而是一个可以被多个业务应用复用的通用 Kernel：

```text
Kernel
  -> 被不同 Application 组合
  -> 被不同 Interface 调用
  -> 被不同 Adapter 承载
```

#### 1.6.1 第一阶段完成定义

第一阶段不是“代码目录创建完成”，而是以下证据全部存在：

1. 真实 Model Smoke 通过。
2. Agent 真实闭环通过。
3. Tool Call、Memory、Streaming、Cancellation 有可观察证据。
4. Workflow 顺序、分支、暂停恢复和幂等测试通过。
5. Core 依赖检查通过。

---

## 2. 核心特点

### 2.1 六个核心原语

| 原语 | 负责什么 | 不负责什么 |
|---|---|---|
| `Agent` | 使用 Model、Instructions、Tools 和 Memory 完成智能任务 | 不拥有业务流程状态，不负责界面输出 |
| `Workflow` | 组合步骤并控制顺序、分支、重试、暂停和恢复 | 不替代 Agent，不以 Agent 数量为目标 |
| `Tool` | 提供结构化的外部动作和执行结果 | 不负责自然语言推理和流程路由 |
| `Memory` | 读取和写入可持久化上下文 | 不负责业务决策、Trace 或 UI 历史 |
| `Model` | 提供模型请求、响应和用量信息 | 不负责业务规则和状态持久化 |
| `Runtime` | 执行 Agent 或 Workflow 的生命周期 | 不负责业务语义 |

### 2.2 通用内核与业务应用分离

Kernel 中禁止出现以下业务内容：

```text
工伤
政策
赔偿
地区
Evidence
```

业务只在应用层组合通用能力：

```text
applications/
  work_injury/
```

### 2.3 全链路可替换

以下实现都只能通过适配器接入：

```text
Model Provider
Memory Store
Runtime Engine
Tool Backend
Interface
```

替换实现不能改变 Kernel 的公共语义。

### 2.4 可独立理解和测试

每个原语都必须能在不阅读业务代码的情况下解释清楚，并能通过公开协议独立测试；涉及模型生成的验收必须使用真实 Model Adapter。

### 2.5 运行过程可解释

运行结果不仅要能返回最终输出，还要能说明：

- 哪个 Agent 或 Workflow 被执行。
- 使用了哪些 Tool、Model 和 Memory。
- 哪一步成功、失败、暂停或取消。
- Adapter 产生的结果如何回到 Kernel。

具体 Trace 字段在后续观测设计中确认，不在本阶段增加新的核心原语。

### 2.6 Execution 执行层

Execution 不是新的 Core 原语，而是统一承载一次运行所需的横切能力：

```text
Execution
  -> Context
  -> Hooks
  -> Guardrails
  -> Retry
  -> Cancellation
  -> Streaming
```

统一规则：

- `Retry` 只处理可安全重试的临时失败。
- `Cancellation` 负责主动终止当前运行，并向下游传播取消信号。
- `Streaming` 负责逐步返回运行事件和输出，不改变业务状态。
- `Hooks` 用于观测和扩展，不接管 Agent 或 Workflow 职责。
- `Guardrails` 负责输入、输出和 Tool 调用边界。
- `Context` 只描述当前运行，不替代 Memory、Workflow 状态或业务数据。

### 2.7 Agent 模块边界

`Agent` 是一个独立的智能执行单元，负责完成一个明确目标：

```text
Agent
  -> Instructions
  -> Model
  -> Tools
  -> Memory
  -> 结构化结果
```

`Agent` 只表达“要完成什么任务”，不负责：

- Workflow 顺序、分支和多 Agent 调度。
- Memory 的底层存储。
- Model Provider 和 Tool Backend 连接。
- UI、API 和业务状态。
- Retry、Cancellation、Streaming 的生命周期控制。

Prompt 所有权保持为：

```text
Application
  -> 提供 Instructions、Prompt 模板和版本
Agent
  -> 将 Instructions、运行输入、Context 和 Memory 组合为 Model Request
Execution
  -> 提供运行约束、Guardrails 和取消信号
Model
  -> 只接收 Model Request 并生成 Response
```

Prompt 模板属于 Application 配置，不成为新的 Core 原语；最终请求组装属于 Agent 的任务执行职责。

运行生命周期由 `Runtime` 和 `Execution` 负责：

```text
Runtime
  -> Execution
      -> Agent
          -> Model
          -> Tool
          -> Memory
```

### 2.8 Tool 模块边界

`Tool` 是一个明确、结构化、可治理的外部动作：

```text
Tool
  -> 输入
  -> 执行
  -> 输出
```

`Tool` 负责：

- 定义一个明确动作。
- 接收和校验结构化输入。
- 调用外部能力。
- 返回结构化结果和明确错误。

`Tool` 不负责：

- 自然语言推理。
- Workflow 路由。
- Prompt 拼接。
- 修改 Agent 或 Workflow 共享状态。
- 决定是否重试。
- UI 和业务流程。

权限、超时、取消、幂等和 Trace 属于 Execution 的治理能力，不扩张为新的核心原语。

### 2.9 Workflow 模块边界

`Workflow` 是确定性的流程组合单元，负责把多个步骤连接起来：

```text
Workflow
  -> Agent
  -> Tool
  -> Function Step
  -> 条件分支
  -> 结构化结果
```

`Workflow` 负责：

- 定义步骤顺序。
- 连接 Agent、Tool 和函数步骤。
- 根据结果进行条件分支。
- 管理流程级执行状态。
- 定义结束条件。
- 支持暂停和恢复。
- 在无依赖步骤之间支持并行。

`Workflow` 不负责：

- 替代 Agent 推理。
- 直接调用 Model Provider。
- 直接实现底层 Tool。
- 管理 Agent 内部状态。
- 管理 Memory 底层存储。
- 承担业务领域规则。

Workflow 状态只保存流程推进所需的信息，不把业务事实、长期记忆或 Trace 当作自己的状态来源。

### 2.10 Memory 模块边界

`Memory` 负责跨运行保存和读取 Agent 需要的上下文：

```text
Memory
  -> read
  -> write
  -> search
```

Memory 可以支持不同使用方式：

```text
对话记忆
工作记忆
语义检索记忆
```

这些属于 Memory 的使用方式，不拆成多个核心原语。

`Memory` 不负责：

- Workflow 当前步骤和流程状态。
- Trace、日志和评测记录。
- UI 展示历史。
- 业务数据库。
- 决定 Agent 下一步做什么。
- 直接调用 Model 或 Tool。

边界保持为：

```text
Memory       = 跨运行保留的上下文
Workflow     = 当前流程推进状态
Execution    = 当前运行生命周期
Observability = 运行证据
```

### 2.11 Model 模块边界

`Model` 是与具体 Provider 无关的模型调用能力：

```text
Model
  -> Request
  -> Provider Adapter
  -> Response
```

`Model` 负责：

- 接收结构化模型请求。
- 调用模型 Provider。
- 返回模型响应。
- 返回 Tool Call 意图。
- 返回 usage 和模型错误。
- 支持结构化输出和流式响应能力。

`Model` 不负责：

- 拼接业务 Prompt。
- 读取和写入 Memory。
- 执行 Tool。
- 决定 Workflow 下一步。
- 处理业务规则。
- 决定是否重试。
- 暴露 Provider SDK 类型。

边界保持为：

```text
Model     = 负责生成
Agent     = 负责完成任务
Tool      = 负责执行动作
Execution = 负责运行治理
```

### 2.12 Runtime 模块边界

`Runtime` 负责执行 Agent 或 Workflow 的完整生命周期：

```text
Runtime
  -> start
  -> execute
  -> pause
  -> resume
  -> cancel
  -> finish
```

`Runtime` 负责：

- 创建一次运行。
- 调用 Agent 或 Workflow。
- 管理运行生命周期。
- 协调 Execution 层。
- 处理暂停、恢复、取消和结束。
- 输出运行结果和运行事件。
- 连接具体 Runtime Adapter。

`Runtime` 不负责：

- Agent 推理逻辑。
- Workflow 业务流程。
- 具体 Tool 执行。
- 直接调用 Model Provider。
- Memory 底层存储。
- 业务事实和业务规则。

所有 Runtime Adapter 都必须遵守同一套 Runtime 协议，不能把具体框架状态泄漏到 Core。

### 2.13 支撑协议边界

支撑协议只服务 Core 和 Execution，不新增第七个核心原语：

```text
Context
  -> 描述当前运行

Events
  -> 描述运行过程

Errors
  -> 描述失败和终止

Core Result
  -> 描述各原语的执行结果
```

`Context` 只保存当前运行所需的元信息；`Events` 只描述生命周期和流式过程；`Errors` 统一错误语义；结果由 Agent、Tool、Workflow 和 Runtime 分别定义，不创建万能结果对象。

### 2.14 Applications 业务组合层

`Application` 是具体业务对 Kernel 能力的组合：

```text
Application
  -> Agent
  -> Workflow
  -> Tool
  -> Memory
  -> Model
  -> Runtime
```

Application 负责：

- 定义业务目标。
- 组合 Kernel 原语。
- 定义业务 Prompt、规则和数据模型。
- 选择业务需要的 Tool。
- 定义业务级测试和评测。
- 提供业务应用入口给 Interface。

Application 不负责：

- 修改 Kernel 原语。
- 把业务概念放入 Core。
- 直接依赖具体 Provider SDK。
- 直接管理 Runtime 内部状态。
- 复制一套 Agent、Tool 或 Workflow 框架。

依赖方向保持为：

```text
Kernel
  <- Application
  <- Interface
```

### 2.15 Interfaces 接口层

`Interface` 是用户或外部系统访问 Application 的入口：

```text
Interface
  -> Application
      -> Workflow / Agent
          -> Model / Tool / Memory
```

Interface 负责：

- 接收外部输入。
- 转换为 Application 请求。
- 调用 Application。
- 转发 Streaming 事件。
- 序列化结构化结果。
- 映射错误和取消状态。
- 提供 CLI、TUI、HTTP 或其他入口。

Interface 不负责：

- Agent 推理。
- Workflow 编排。
- Tool 执行。
- Memory 存储。
- Model Provider 调用。
- 业务规则。
- 修改 Kernel 协议。

Interface 不能绕过 Application 直接拼接 Agent、Tool 或 Model。

### 2.16 外围能力归属

以下能力属于系统外围能力，不新增 Core 原语：

| 能力 | 归属 | 当前第一阶段 |
|---|---|---|
| Prompt 模板和版本 | Application 配置 | 只定义所有权，不实现业务 Prompt |
| Observability | Execution / Runtime 横切能力 | 记录最小运行事件和错误 |
| Evals | System / QA | 先建立 Kernel contract 和纵向切片验收 |
| Security | Execution Guardrails / Interface | 先定义权限、取消和敏感输入边界 |
| Integrations | Adapters | 先接入真实 Model Adapter，其他外部能力保持最小实现 |
| RAG | Application / Integrations | 不进入 Kernel |
| Deployment | Product / Interface | 不进入第一阶段 |
| Triggers / Actions | Product / Interface | 不进入第一阶段 |

这些能力必须有明确的归属和非目标，不能因为暂未实现而继续悬空，也不能为了对齐参考项目而提前进入 Kernel。

### 2.17 核心能力验收视图

| 能力主题 | 核心问题 | 第一阶段证据 |
|---|---|---|
| 智能执行 | Agent 能否使用真实 Model 完成任务？ | K-001、K-002 |
| 流程控制 | Workflow 能否稳定推进、暂停和恢复？ | K-004、K-005 |
| 外部动作 | Tool 是否结构化、可校验、可取消和可幂等？ | K-003 |
| 上下文 | Memory 是否跨运行保存且作用域隔离？ | K-006 |
| 运行治理 | Runtime 是否正确处理事件、取消和流式？ | K-008 |
| 架构边界 | Core 是否不依赖外部层？ | K-009 |
| 端到端效果 | 真实模型闭环是否可复核？ | K-010 |

### 2.18 设计取舍

本项目明确选择：

| 选择 | 原因 |
|---|---|
| 真实 Model 优先 | 只有真实调用才能验证 Agent、Tool Call 和输出结构 |
| In-memory Memory 起步 | 缩小第一条切片范围，不冻结生产存储 |
| 无副作用 Tool 起步 | 验证 Tool 协议、权限和错误，不引入业务外部系统 |
| Runtime 先单进程 | 先验证生命周期语义，再考虑远程或分布式 |
| Application 延后 | 防止业务需求反向污染 Kernel |
| 事件而非日志拼接 | 让 Streaming、Trace、Eval 和 Interface 共用运行证据 |

---

## 3. 技术选型

### 3.1 技术选型原则

技术选型服从 Kernel 边界，而不是反过来让某个框架决定 Kernel：

| 原则 | 具体要求 |
|---|---|
| 运行环境 | Python 3.11，使用 `uv` 管理环境、依赖和命令 |
| 异步边界 | Model、Tool、Memory、Runtime 的外部调用保留异步能力 |
| 供应商隔离 | Provider SDK 只能存在于 Adapter |
| 先小后大 | 单进程、内存存储和一个真实 Model 先验证语义 |
| 可测试 | 每个协议有结构化输入、输出、错误和验收证据 |
| 可替换 | 替换实现不改变 Core 公共语义 |

### 3.2 Kernel Runtime 设计

#### 3.2.1 Agent 调用协议

Agent 不直接依赖 Provider，而是构造统一的 `ModelRequest`：

```text
ModelRequest
  -> instructions
  -> input
  -> context
  -> memory_items
  -> tool_schemas
  -> output_schema
  -> runtime_metadata
```

Model Adapter 返回统一的 `ModelResponse`：

```text
ModelResponse
  -> text / structured_output
  -> tool_calls
  -> usage
  -> finish_reason
  -> provider_metadata
  -> error
```

Provider 具体字段只能进入 `provider_metadata` 或 Adapter 内部，不能进入 Agent、Workflow 或 Application 公共协议。

#### 3.2.2 Workflow 状态协议

Workflow 状态只服务流程恢复：

```text
WorkflowState
  -> workflow_id
  -> run_id
  -> current_step
  -> completed_steps
  -> step_results
  -> branch_values
  -> pause_reason
  -> resume_token
```

状态规则：

- 已完成步骤必须可识别。
- 有副作用的步骤必须有幂等键。
- 暂停恢复不能依赖 Memory 或 Trace 反推当前步骤。
- 业务事实通过 Application 数据模型传递，不写入 Core Workflow State。

### 3.3 Adapter 与具体实现

Kernel 只定义协议，Adapter 负责连接具体技术：

```text
Kernel Protocol
  -> Model Adapter
  -> Memory Adapter
  -> Tool Adapter
  -> Runtime Adapter
```

#### 3.3.1 Model Provider Adapter

第一条切片接入真实模型：

| 配置 | 当前值 |
|---|---|
| 模型选择 | `ANANHU_REAL_MODEL` |
| 当前模型 | `doubao-seed-2-0-mini-260428` |
| Smoke 开关 | `ANANHU_REAL_MODEL_SMOKE` |
| 替换边界 | `Model Protocol` |

Adapter 必须负责：

- Provider 认证和请求格式转换。
- 超时、错误和 usage 归一化。
- Tool Schema 和结构化输出转换。
- 流式增量转换为 Kernel Events。
- 记录模型标识和 Provider 元信息。

#### 3.3.2 Memory Adapter

第一条切片采用 In-memory Adapter：

| 操作 | 要求 |
|---|---|
| `read` | 按 scope 读取上下文 |
| `write` | 写入带来源和时间的记忆项 |
| `search` | 在同一 scope 内查询相关项 |
| 隔离 | 不同 session / user / application scope 不串数据 |
| 替换 | 不改变 Agent 对 Memory Protocol 的调用 |

#### 3.3.3 Tool Adapter

第一条切片采用一个无副作用结构化 Tool，验证：

```text
输入 Schema
  -> 权限检查
  -> 执行
  -> 输出 Schema
  -> 错误和幂等证据
```

Tool Adapter 不处理自然语言，不决定 Workflow 路由，不读取 Provider SDK 配置。

#### 3.3.4 Runtime Adapter

第一条切片采用单进程本地 Runtime：

- 保存 Run 生命周期状态。
- 依次发出 started、step、tool、stream、completed / failed / cancelled Events。
- 支持取消和最小暂停恢复。
- 不暴露具体工作流库类型。

### 3.4 Execution 执行支撑

#### 3.4.1 Context

Context 只表示当前运行：

```text
run_id
parent_run_id
input
metadata
deadline
cancellation
```

Context 不替代 Memory、Workflow State、Trace 或业务数据。

#### 3.4.2 Retry 与幂等

Retry 只适用于明确可重试的临时错误：

| 错误 | 默认策略 |
|---|---|
| Provider 临时网络错误 | 有上限重试 |
| Provider 限流 | 按错误信息和退避策略重试 |
| Tool 超时 | 只有 Tool 声明幂等时重试 |
| Schema / 权限错误 | 不重试 |
| 取消错误 | 不重试 |

每次重试必须记录 attempt、原因、延迟和最终结果。

#### 3.4.3 Cancellation、Streaming 和 Hooks

- Cancellation 向 Model、Tool、Memory 和 Workflow 传播。
- Streaming 只发送增量事件，不修改最终结果语义。
- Hooks 只观察或扩展生命周期，不接管 Core 职责。
- Guardrails 在输入、Model 输出和 Tool 调用前后执行。

### 3.5 配置管理与切换流程

配置由外层读取、校验和注入：

```text
环境变量 / 配置文件
  -> Adapter Config
  -> Schema 校验
  -> 创建 Model / Memory / Tool / Runtime Adapter
  -> 注入 Application 或测试 Fixture
```

当前最小配置：

```text
ANANHU_REAL_MODEL=doubao-seed-2-0-mini-260428
ANANHU_REAL_MODEL_SMOKE=0|1
```

切换流程：

1. 修改模型标识或 Adapter 配置。
2. 校验凭证、依赖和网络。
3. 开启真实 Smoke。
4. 记录模型标识、usage、延迟和错误。
5. 通过后再进入 Agent Integration。

### 3.6 可观测性与评估接入

第一阶段不建立 Dashboard，但必须保留运行证据：

```text
Runtime
  -> Events Collector
      -> run_id
      -> event_type
      -> timestamp
      -> component
      -> provider / method
      -> duration
      -> usage
      -> error
```

Evals 在 Application 之前只验证 Kernel 契约和真实纵向切片；业务质量评估在 Application 建立后独立维护。

### 3.7 第一条纵向切片技术基线

| 能力 | 第一阶段选择 | 替换边界 |
|---|---|---|
| Model | 真实 Model Provider Adapter | Model Protocol |
| Memory | In-memory Adapter | Memory Protocol |
| Tool | 无副作用结构化 Tool | Tool Protocol |
| Runtime | 单进程本地 Runtime | Runtime Protocol |
| Interface | 程序化测试入口 | Interface Protocol |
| Observability | 内存 Events Collector | Events / Trace Adapter |

真实模型是必选依赖；其他最小实现只用于缩小系统范围，不模拟模型行为。

---

## 4. 测试方案

### 4.1 测试理念：测试驱动开发 (TDD)

测试不是实现完成后的附加步骤，而是每个 Core 协议的行为说明：

- 先写输入、输出、错误和边界测试，再实现最小代码。
- 单元测试保持快速，真实模型测试单独标记并记录成本。
- 测试失败必须暴露真实错误，不通过替代输出掩盖失败。
- 每个任务必须关联至少一个验收 ID 和一个可复核证据。

测试金字塔：

```text
             E2E / Application
          Real Model Integration
       Contract / Architecture Tests
             Unit Tests
```

### 4.2 测试分层策略

#### 4.2.1 Core 单元测试 (Unit Tests)

目标：验证不依赖业务、Provider 和外部界面的确定性逻辑。

| 模块 | 测试重点 | 典型用例 |
|---|---|---|
| Agent | 请求组装、结果解析、Tool Call 状态 | 缺少输入、非法 Tool Call、结构化结果 |
| Workflow | 顺序、分支、暂停位置、幂等键 | 分支选择、重复恢复、错误终止 |
| Tool | Schema、权限、超时、错误映射 | 缺字段、权限拒绝、取消传播 |
| Memory | scope、读写、搜索、序列化 | 同 scope 可读、跨 scope 隔离 |
| Model | Request / Response Schema | Tool Call 解析、usage 归一化、错误转换 |
| Runtime | 生命周期、事件顺序、只结束一次 | complete、failed、cancelled、resume |

Core 单元测试不得依赖工伤业务、具体界面或 Provider SDK。

#### 4.2.2 Adapter Contract Tests

所有 Adapter 必须通过同一份公开协议合同：

| Adapter | 必须证明 |
|---|---|
| Model Adapter | 请求、结构化输出、Tool Call、usage 和错误语义稳定 |
| Memory Adapter | read / write / search、scope 隔离和序列化稳定 |
| Tool Adapter | 输入校验、输出 Schema、超时、取消和幂等稳定 |
| Runtime Adapter | 生命周期、事件顺序、暂停恢复和取消稳定 |

合同测试不验证内部实现，只验证公开行为。

#### 4.2.3 Architecture Tests

自动检查：

- `agent_kernel/` 不导入 `applications/`、`interfaces/`。
- Core 不导入具体 Provider SDK、数据库驱动或工作流框架。
- Adapter 只能实现 Kernel Protocol，不能把实现类型泄漏到 Core。
- Application 只能依赖 Kernel 公开协议。
- `tests/integration/real_model_fixture/` 不得被 Core 反向导入。
- 旧项目协议不成为新 Kernel 的共享入口。

#### 4.2.4 Kernel Integration Tests

目标：验证多个 Core 协同后的运行链路：

| 场景 | 操作 | 预期结果 |
|---|---|---|
| Agent + Memory | 写入记忆后执行 Agent | Agent 读取到同 scope 上下文 |
| Agent + Tool | Model 返回 Tool Call | Tool 执行后结果回到 Model |
| Runtime + Agent | 启动并完成一次 Run | 结果和 Events 一致 |
| Workflow + Agent | 执行多个步骤 | 顺序、分支和结果正确 |
| Cancellation | 运行中主动取消 | 下游收到取消且只结束一次 |

#### 4.2.5 真实模型 Smoke / Integration

目标：验证真实效果，不验证固定文本：

1. 校验 `ANANHU_REAL_MODEL` 和 Provider 凭证。
2. 使用固定、低成本、可重复输入。
3. 真实发送 Model Request。
4. 验证结构化输出、usage、Tool Call 或错误。
5. 验证 Events 顺序、延迟和取消传播。
6. 保存模型标识、请求摘要、结果摘要和错误证据。

约束：

- `ANANHU_REAL_MODEL_SMOKE=1` 才执行网络测试。
- 未开启时必须明确显示“未执行”，不能显示“通过”。
- Provider 不可用时必须失败或阻塞，不使用模拟输出。
- 不对自然语言全文做脆弱匹配，优先断言 Schema、状态和事件。

#### 4.2.6 End-to-End Tests

第一阶段只覆盖 Kernel 端到端场景：

**场景 1：真实 Agent 闭环**

- 启动程序化测试入口。
- 加载真实 Model Adapter、In-memory Memory 和无副作用 Tool。
- 发送固定输入。
- 验证 Model -> Tool -> Memory -> Result 的完整链路。

**场景 2：Workflow 暂停恢复**

- 执行到明确暂停点。
- 保存 Workflow State。
- 恢复 Run。
- 验证已完成副作用步骤不重复。

**场景 3：运行取消和流式**

- 启动一个可观察的长运行。
- 接收增量 Events。
- 发送取消。
- 验证下游终止、事件顺序和最终状态。

业务 Application、CLI、HTTP 和 Dashboard 的 E2E 在后续阶段独立维护。

### 4.3 Kernel 质量评估

质量评估不以主观“看起来能跑”为准，至少记录：

| 评估维度 | 指标或证据 |
|---|---|
| 协议稳定性 | Contract Tests 通过率 |
| 真实模型效果 | 结构化结果成功率、Tool Call 成功率 |
| 运行可靠性 | 取消成功率、只结束一次、错误分类 |
| 上下文正确性 | Memory scope 隔离、恢复位置正确 |
| 可观测性 | Events 完整率、usage 和延迟记录完整率 |
| 回归情况 | Golden Inputs 的结果结构和关键状态无回归 |

业务质量指标在 Application 建立后增加，不把业务指标硬编码进 Kernel。

### 4.4 性能与压力测试（可选）

当前项目是单进程 Kernel 验证阶段，性能测试不是发布门禁，但保留基准入口：

| 测试类型 | 验证点 | 工具或方法 | 优先级 |
|---|---|---|---|
| Model 延迟 | Provider P50 / P95 | Events 时间戳 | 中 |
| Runtime 开销 | 非 Model 部分耗时 | 本地 benchmark | 中 |
| Memory 性能 | read / write / search 延迟 | pytest benchmark | 低 |
| 并发取消 | 多 Run 取消传播 | asyncio 场景测试 | 低 |
| 长运行内存 | Events 和 Context 是否泄漏 | memory profiler | 低 |

性能数据不能替代正确性测试。

### 4.5 测试工具链与 CI/CD

本地测试命令统一通过 `uv`：

```bash
uv run pytest -q tests/contract tests/architecture
uv run pytest -q tests/integration
ANANHU_REAL_MODEL_SMOKE=1 uv run pytest -q tests/integration/real_model_fixture
```

CI 分层：

1. 每次提交：文档检查、静态检查、Unit、Contract、Architecture Tests。
2. 具备凭证的受控环境：Real Model Smoke / Integration。
3. 合并前：完整 Kernel Integration 和 E2E。
4. 定期任务：真实模型成本、延迟和 Golden Input 回归。

真实模型凭证不能写入仓库；CI 没有凭证时只能报告“未执行”，不能标记真实模型验收通过。

### 4.6 测试失败处理和证据

每次失败至少记录：

```text
test_id
run_id
model_id
provider
input_summary
expected
actual
events
usage
latency
error_type
retry_count
```

失败分类：

| 类别 | 处理 |
|---|---|
| 协议失败 | 阻塞合并，先修复契约 |
| 架构依赖失败 | 阻塞实现，先修复边界 |
| 真实模型配置失败 | 标记阻塞，不改用替代模型 |
| Provider 临时失败 | 按 Retry 规则重试，记录最终结果 |
| 断言失败 | 生成 badcase，保留输入和运行证据 |

### 4.7 Kernel 验收矩阵

| ID | 验收场景 | 可观察结果 | 证据 |
|---|---|---|---|
| K-001 | Agent 使用真实 Model Provider 完成一次任务 | 返回结构化 Agent Result，并记录模型标识和 usage | Real Model Integration |
| K-002 | Agent 触发一个 Tool | 输入校验、Tool Result 和后续 Model 调用顺序正确 | 运行事件 |
| K-003 | Tool 输入错误、超时和取消 | 返回稳定 Error，不执行非法动作 | Contract Test |
| K-004 | Workflow 顺序和条件分支 | 步骤顺序、分支结果和结束原因正确 | Workflow Test |
| K-005 | Workflow 暂停和恢复 | 从暂停位置继续，不重复已完成副作用步骤 | Runtime Test |
| K-006 | Memory 写入后再次读取 | 读取到同一作用域的上下文，其他作用域隔离 | Memory Test |
| K-007 | 真实 Model Adapter 按协议接入 | Agent 公共协议、结构化结果和错误语义稳定 | Real Model Contract |
| K-008 | Runtime 取消和流式输出 | 事件顺序完整，取消向下游传播且只结束一次 | Execution Test |
| K-009 | 架构依赖检查 | Core 不导入 Application、Provider、Interface 或具体 Runtime | Architecture Test |
| K-010 | 第一条真实模型纵向切片 | Agent、Tool、Memory、Model、Runtime 和 Events 闭环通过 | Real Model Integration |

任何实现任务必须至少关联一个验收 ID，不能只写“完成模块实现”。

---

## 5. 系统架构与模块设计

### 5.1 整体架构图

系统由外到内分为 Interface、Application、Runtime、Execution、Core 和 Adapter。配置链路与执行链路必须分开：

```text
┌──────────────────────────────────────────────────────────────┐
│ Interface / Programmatic Test Entry                         │
│ 输入转换、事件转发、结果序列化、错误映射                      │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Application / Test Fixture                                  │
│ 组装 Agent、Workflow、Tool、Memory、Model，不实现 Runtime     │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Runtime                                                      │
│ 创建 Run，协调 Execution，执行 Agent 或 Workflow              │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ Execution                                                    │
│ Context、Hooks、Guardrails、Retry、Cancellation、Streaming    │
└───────────────┬──────────────────┬───────────────────────────┘
                │                  │
       ┌────────▼────────┐ ┌───────▼────────┐
       │ Agent / Workflow│ │ Events / Result│
       └───┬─────┬───────┘ └────────────────┘
           │     │
     ┌─────▼─┐ ┌─▼────┐ ┌────────┐
     │ Model │ │ Tool │ │ Memory │
     └───────┘ └──────┘ └────────┘

Adapter 只实现上述协议，Provider、存储和运行时框架不能进入 Core。
```

依赖方向固定为：

```text
Interface -> Application / Test Fixture -> Kernel
Adapter -> Kernel Protocol
Runtime -> Execution -> Agent / Workflow -> Model / Tool / Memory
```

### 5.2 目录结构与交付清单

目录结构必须能直接对应实施任务：

```text
src/
  agent_kernel/
    agent/
    workflow/
    tool/
    memory/
    model/
    runtime/
  adapters/
    model/
    memory/
    tool/
    runtime/
applications/
interfaces/
tests/
  contract/
  integration/
    real_model_fixture/
  architecture/
```

目录职责：

| 目录 | 责任 | 当前阶段 |
|---|---|---|
| `src/agent_kernel/` | 六个 Core 的公开协议和实现 | 第一阶段建立 |
| `src/adapters/` | 真实 Model、Memory、Tool、Runtime 的具体接入 | 第一阶段建立最小实现 |
| `applications/` | 具体业务组合 | Kernel 验收前保持为空 |
| `interfaces/` | CLI、SDK、HTTP 等外部入口 | Application 稳定后接入 |
| `tests/contract/` | 协议和依赖方向测试 | 与 Core 同步建立 |
| `tests/integration/real_model_fixture/` | 真实模型闭环测试 | 第一条纵向切片 |
| `tests/architecture/` | 防止 Core 依赖外层 | K-01 建立 |

`Context`、`Hooks`、`Guardrails`、`Retry`、`Cancellation` 和 `Streaming` 是 Runtime 的执行支撑，不各自建立新的 Core 目录。

### 5.3 Core 模块设计

每个 Core 模块按“目标、输入、输出、执行步骤、边界、错误和验收”描述，避免只写抽象名词。

#### 5.3.1 Agent

目标：使用 Instructions、Model、Tool 和 Memory 完成一个明确的智能任务。

输入：

```text
AgentInput
  -> task_input
  -> instructions_version
  -> Model
  -> allowed Tools
  -> Memory scope
  -> Execution Context
```

执行步骤：

1. 读取当前运行需要的 Memory。
2. 组装最终 Model Request。
3. 调用真实 Model Adapter。
4. 如果返回 Tool Call，经过 Execution 校验后执行 Tool。
5. 将 Tool Result 回传 Model，直到得到最终结果或达到运行上限。
6. 返回结构化 Agent Result。

输出：

```text
AgentResult
  -> output
  -> tool_calls
  -> usage
  -> stop_reason
  -> error
```

边界：

- Agent 不负责 Workflow 顺序、Runtime 生命周期、Provider SDK、Tool 后端或 Memory 存储。
- Agent 不直接拼接业务流程，只使用 Application 提供的 Instructions 和输入。
- Agent 必须保持单次运行无共享可变状态。

验收：K-001、K-002、K-007。

#### 5.3.2 Workflow

目标：以确定性步骤组合 Agent、Tool 和函数步骤。

输入：

```text
WorkflowInput
  -> workflow_id
  -> steps
  -> initial_input
  -> workflow_state
```

步骤类型：

| 步骤 | 作用 |
|---|---|
| Agent Step | 调用一个 Agent 完成智能任务 |
| Tool Step | 执行一个明确的结构化动作 |
| Function Step | 执行确定性的数据转换或条件判断 |
| Branch | 根据上一步结果选择下一步 |

状态至少包含当前步骤、已完成步骤结果、下一步条件、暂停位置和结束原因。已完成的副作用步骤必须具备幂等保护。

边界：

- Workflow 不实现 Model、Tool 或 Memory。
- Workflow 不保存长期记忆、Trace 或业务数据库。
- Workflow 可以表达流程规则，但不把业务领域概念写进 Core。

验收：K-004、K-005。

#### 5.3.3 Tool

目标：提供一个明确、结构化、可治理的外部动作。

执行流程：

```text
结构化输入
  -> Schema 校验
  -> Guardrails / Permission 检查
  -> 幂等键检查
  -> 外部动作
  -> 结构化输出或明确错误
```

Tool 必须定义输入 Schema、输出 Schema、权限要求、超时、取消行为、幂等语义和错误类别。Tool 不决定是否重试，不负责自然语言推理和 Workflow 路由。

验收：K-002、K-003、K-005。

#### 5.3.4 Memory

目标：跨运行保存和读取 Agent 所需上下文。

操作：

```text
read(scope, query)
write(scope, items)
search(scope, query, limit)
```

每条记忆必须带有作用域、内容、来源和写入时间。不同作用域必须隔离。Memory 不保存 Workflow 当前步骤、完整 Trace、UI 历史或业务数据库事实。

第一条切片使用 In-memory Adapter，但必须通过 Memory Protocol，后续可替换文件、数据库或语义检索存储。

验收：K-006、K-010。

#### 5.3.5 Model

目标：提供与 Provider 无关的模型请求和响应协议。

请求至少包含 Instructions、输入、上下文、Tool Schema、输出格式要求和运行元信息；响应至少包含文本或结构化输出、Tool Call 意图、usage、finish reason 和错误。

真实模型要求：

- 第一条纵向切片使用 `ANANHU_REAL_MODEL` 配置的真实模型。
- Provider 凭证、网络或模型错误必须原样映射为 Kernel 错误，不允许改用替代输出。
- Provider SDK 类型只能存在于 Model Adapter。

验收：K-001、K-007、K-010。

#### 5.3.6 Runtime

目标：负责 Agent 或 Workflow 的完整运行生命周期。

生命周期：

```text
start
  -> execute
  -> pause / resume
  -> cancel
  -> complete / fail
```

Runtime 负责 Run ID、Context、事件顺序、取消传播、暂停恢复和最终 Runtime Result。Runtime 不负责业务流程、Agent 推理、Tool 实现、Memory 存储或 Model Provider 调用。

验收：K-005、K-008、K-010。

### 5.4 执行流程

#### 5.4.1 Agent 单次运行

```text
Runtime.start
  -> Context 初始化
  -> Agent 读取 Memory
  -> Model 生成
  -> Tool Call（可选）
  -> Tool Result 回传 Model
  -> 结构化 Agent Result
  -> Runtime Result
```

#### 5.4.2 Workflow 运行

```text
Runtime.start
  -> Workflow 读取 workflow_state
  -> 执行当前 Step
  -> 保存 Step Result
  -> Branch 决定下一 Step
  -> 完成、暂停或失败
```

#### 5.4.3 真实模型 Smoke

Smoke 测试至少执行：

1. 读取 `ANANHU_REAL_MODEL`。
2. 校验 Provider 配置和凭证。
3. 发送固定低成本请求。
4. 验证结构化响应、usage 和错误映射。
5. 保存模型标识、延迟、事件和结果摘要。

`ANANHU_REAL_MODEL_SMOKE` 未开启时，测试必须明确报告未执行；凭证或网络不可用时必须失败或阻塞，不能静默跳过。

#### 5.4.4 Retry、Cancellation 和 Streaming

| 能力 | 触发 | 结果 |
|---|---|---|
| Retry | 可安全重试的临时错误 | 在上限内重新执行，不重复不可幂等副作用 |
| Cancellation | 用户或系统主动停止 | 向 Model、Tool、Memory 和 Workflow 传播，最终只结束一次 |
| Streaming | 运行过程中产生增量事件 | 按顺序输出，不改变 Workflow 状态和 Memory 事实 |
| Pause / Resume | Workflow 到达等待点 | 保存恢复所需状态，从明确步骤继续 |

### 5.5 配置驱动设计

Provider 和运行参数在外层配置，Core 只接收已经校验的协议对象：

```text
ANANHU_REAL_MODEL=doubao-seed-2-0-mini-260428
ANANHU_REAL_MODEL_SMOKE=0|1

Model Adapter
  -> provider configuration
  -> credential reference
  -> model identifier
  -> timeout / retry policy

Runtime
  -> receives validated configuration
  -> does not read provider SDK configuration directly
```

配置规则：

- 环境变量和密钥只由 Adapter / Interface 读取，不能进入 Core。
- 模型标识、Provider、超时、重试上限和输出格式必须可记录。
- 配置错误在运行开始前失败，不等到 Model 调用中才发现。
- 生产级多 Provider 路由暂不冻结，第一条切片只固定一个真实模型。

### 5.6 扩展性设计要点

新增能力必须遵循“实现既有协议、增加测试、更新规格”的顺序：

1. 新增 Model Provider：实现 Model Adapter，不修改 Agent 和 Model Protocol。
2. 新增 Memory 存储：实现 Memory Adapter，不修改 Agent 的记忆使用方式。
3. 新增 Tool：定义结构化 Schema、权限、幂等和错误，挂入 Application 或测试 Fixture。
4. 新增 Workflow：组合已有 Agent、Tool 和函数步骤，不新增 Orchestrator。
5. 新增业务：只在 `applications/<业务>/` 组合 Kernel，不把业务词汇写回 Core。
6. 新增 Interface：只做输入转换、调用、事件转发、结果序列化和错误映射。
7. 新增 Observability：通过 Events / Hooks 扩展，不修改 Core 结果语义。

### 5.7 Core Contract Matrix

| 原语 | 最小输入 | 最小输出 | 主要错误 | 生命周期 | 替换点 |
|---|---|---|---|---|---|
| Agent | input、Instructions、Tools、Memory | output、tool_calls、usage、stop_reason | model、tool、policy、internal | run -> complete / fail / cancel | Agent 配置 |
| Workflow | workflow input、steps、条件 | step_results、output、stop_reason | step、branch、pause、resume | start -> step -> pause / finish | Workflow 实现 |
| Tool | 结构化 input、Execution Context | 结构化 output | validation、permission、timeout、execution | validate -> execute -> result | Tool Adapter |
| Memory | read / write / search 请求 | context items / write result | scope、storage、serialization | read / write / query | Memory Adapter |
| Model | Model Request | response、tool_call、usage | provider、timeout、format | request -> response / error | Model Adapter |
| Runtime | Run Request、Agent 或 Workflow | events、Runtime Result | runtime、cancel、timeout、internal | start -> execute -> pause / resume -> finish | Runtime Adapter |

### 5.8 第一条真实模型纵向切片

第一条切片是 Kernel 验证 Fixture，不是业务功能：

```text
tests/integration/real_model_fixture
  -> Runtime
      -> Execution
          -> Agent
              -> Real Model Provider Adapter
              -> In-memory Memory
              -> No-side-effect Tool
          -> Events
      -> Runtime Result
```

交付标准：

- 真实完成一次 Model 生成。
- 真实完成一次可选 Tool Call。
- 完成一次 Memory 写入和再次读取。
- 返回结构化 Agent Result 和 Runtime Result。
- 覆盖成功、Tool 输入错误、取消和流式事件。
- 保存足以复核的模型标识、usage、事件序列、延迟和错误证据。

---

## 6. 项目排期

### 6.1 排期原则

排期严格对齐第 5 章的目录和运行链路：

- 只按本规格落地，每个任务必须在文件系统或测试证据中产生可见变化。
- 每个任务必须同时写出目标、输出、验收标准和验证方法。
- 先打通真实模型主闭环，再补齐 Workflow、合同测试和外围能力。
- 真实模型不在单元测试中伪造；需要真实效果的场景必须开启真实 Smoke / Integration。
- 每个任务只解决一个边界问题，避免把 Core、Application 和 Interface 一次性混合实现。
- Kernel 验收通过前不创建业务 Application，架构版本发布前不扩展外部 Interface。

### 6.2 阶段总览（大阶段 -> 目的）

| 阶段 | 名称 | 目的 | 状态 |
|---|---|---|---|
| A | 规格和测试基座 | 冻结 Core 契约、目录和架构依赖规则 | 已完成，待审查 |
| B | Core 协议骨架 | 建立六个 Core 的最小公开协议 | 待开始 |
| C | 真实 Model 和最小 Adapter | 接入真实模型、Memory 和 Tool | 待开始 |
| D | Agent 主闭环 | 真实完成 Model、Tool Call、Memory 和结构化输出 | 待开始 |
| E | Runtime 和 Workflow | 补齐生命周期、Streaming、Cancellation、暂停恢复和幂等 | 待开始 |
| F | 合同与集成验收 | 完成 Contract、Integration 和 Architecture Tests | 待开始 |
| G | 第一个架构版本 | 固化完整架构快照、迁移和限制 | 待开始 |
| H | Application 和 Interface | 在 Kernel 之上组合业务并提供外部入口 | 待开始 |

### 6.3 进度跟踪表

状态说明：`[ ]` 未开始，`[~]` 进行中，`[x]` 已完成，`[!]` 阻塞。

#### 阶段 A：规格和测试基座

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| A1 | Core、Execution、外围边界确认 | [x] | 六原语和三层结构 | 设计记录 |
| A2 | 对抗性规格审查修订 | [x] | `DEV_SPEC v0.15` | 文档一致性检查 |
| A3 | 第 1-10 章按参考结构重写 | [x] | `DEV_SPEC v0.16` | 文档结构和链接检查 |

#### 阶段 B：Core 协议骨架

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| B1 | 建立六个 Core 的最小协议 | [ ] | `src/agent_kernel/` 骨架 | Architecture Test |
| B2 | 建立 Core 依赖方向检查 | [ ] | 禁止反向依赖规则 | Architecture Test |
| B3 | 建立错误、事件和结果最小 Schema | [ ] | 公共协议 Schema | Contract Test |

#### 阶段 C：真实 Model 和最小 Adapter

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| C1 | 接入真实 Model Provider Adapter | [ ] | `ANANHU_REAL_MODEL` 配置校验 | Real Model Smoke |
| C2 | 建立 In-memory Memory Adapter | [ ] | 作用域隔离读写 | Memory Contract Test |
| C3 | 建立无副作用 Tool Adapter | [ ] | 输入、输出、错误和幂等 Schema | Tool Contract Test |

#### 阶段 D：Agent 主闭环

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| D1 | Agent 组装真实 Model Request | [ ] | Instructions、Context、Memory 组装 | Real Model Integration |
| D2 | Agent 处理真实 Tool Call | [ ] | Model -> Tool -> Model 循环 | Tool Call Integration |
| D3 | Agent 返回结构化结果和 usage | [ ] | Agent Result | K-001、K-002、K-007 |

#### 阶段 E：Runtime 和 Workflow

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| E1 | Runtime 生命周期和 Events | [ ] | start / execute / finish | Runtime Test |
| E2 | Cancellation、Streaming 和 Retry | [ ] | 传播和只结束一次保证 | Execution Test |
| E3 | Workflow 顺序、分支和暂停恢复 | [ ] | Workflow State | K-004、K-005 |

#### 阶段 F：合同与集成验收

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| F1 | 六个 Core Contract Tests | [ ] | 协议行为证据 | Contract Test |
| F2 | 真实模型纵向切片 | [ ] | Model、Agent、Tool、Memory、Runtime 闭环 | K-010 |
| F3 | Architecture Tests 和依赖扫描 | [ ] | Core 边界证据 | K-009 |

#### 阶段 G：架构版本

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| G1 | 创建第一个完整架构版本 | [ ] | `docs/architecture/versions/` 快照 | 架构版本检查 |
| G2 | 更新架构入口和 changelog | [ ] | 版本索引和变更记录 | 文档链接检查 |

#### 阶段 H：Application 和 Interface

| 任务编号 | 任务名称 | 状态 | 交付物 | 验证方法 |
|---|---|---|---|---|
| H1 | 创建第一个业务 Application | [ ] | `applications/<业务>/` | Application Integration |
| H2 | 接入第一个 Interface | [ ] | CLI 或其他入口 | Interface E2E |
| H3 | 建立业务 Evals 和运行观测 | [ ] | Trace、Eval、Badcase 记录 | Evals / Observability |

### 6.4 阶段门禁

```text
阶段 A 审查通过
  -> 阶段 B Core 协议可测试
  -> 阶段 C 真实 Model Smoke 通过
  -> 阶段 D Agent 主闭环通过
  -> 阶段 E Runtime / Workflow 控制通过
  -> 阶段 F Contract / Integration / Architecture Tests 通过
  -> 阶段 G 第一个架构版本发布
  -> 阶段 H Application / Interface
```

任何阶段未通过，不得跳到下一个阶段。每次完成任务后必须同步更新本表、验收证据和对应版本文档。

## 7. 可扩展性与未来展望

### 7.1 新增业务 Application

新增业务只新增 Application：

```text
applications/
  work_injury/
  customer_service/
  legal_consultation/
```

Application 必须包含：

| 内容 | 责任 |
|---|---|
| Agents | 面向业务目标配置 Agent |
| Workflows | 组合业务流程 |
| Tools | 定义业务动作和权限 |
| Prompts | 管理业务 Instructions 和版本 |
| Policies | 保存业务规则，不进入 Core |
| Evals | 维护业务 Golden Inputs 和质量指标 |

新增业务流程：

1. 先确认 Kernel 公开协议是否足够。
2. 在 `applications/<业务>/` 组合 Agent、Workflow、Tool、Memory 和 Model。
3. 添加业务 Evals 和 Trace 字段。
4. 不修改 Core，不复制一套 Agent Framework。

### 7.2 新增 Agent

只有当任务具备以下独立边界时，才新增 Agent：

- 独立目标。
- 独立 Instructions 和版本。
- 独立 Tool 集合。
- 独立 Memory 读取范围。
- 独立输出 Schema。
- 独立测试和评估边界。

“多 Agent”不是架构目标；如果一个 Agent 可以完成目标，不拆分为多个 Agent。

### 7.3 新增 Workflow

Workflow 扩展只允许增加步骤组合，不允许创建新的总控抽象：

```text
已有 Agent / Tool / Function Step
  -> 顺序
  -> 条件分支
  -> 暂停恢复
  -> 并行（无共享副作用时）
```

新增 Workflow 必须明确：

| 字段 | 要求 |
|---|---|
| 输入 | 结构化 Workflow Input |
| 状态 | 当前步骤和恢复数据 |
| 副作用 | 幂等键、重试和取消行为 |
| 结束 | 成功、失败、暂停、取消 |
| 验收 | 顺序、分支、恢复和重复执行测试 |

### 7.4 新增 Tool

每个 Tool 只有一个明确动作，并具备：

```text
结构化输入
结构化输出
明确错误
明确权限
超时和取消
幂等语义
可测试行为
```

Tool 扩展流程：

1. 定义输入和输出 Schema。
2. 定义权限和敏感数据边界。
3. 定义是否幂等以及重试策略。
4. 实现 Tool Adapter。
5. 添加 Contract、Integration 和 Application 测试。

### 7.5 新增 Model、Memory 或 Runtime

新增 Provider 或后端只能实现既有协议：

| 扩展对象 | 必须实现 | 不能改变 |
|---|---|---|
| Model Provider | Model Request / Response、usage、错误和流式映射 | Agent 和 Application 协议 |
| Memory Store | read / write / search、scope 隔离 | Memory 使用方式 |
| Runtime Engine | 生命周期、事件、取消、暂停恢复 | Workflow 和 Agent 职责 |

替换后必须重新运行对应 Adapter Contract Tests 和真实纵向切片。

### 7.6 新增 Interface、Observability 和 Evals

#### Interface

Interface 只负责：

```text
外部输入
  -> Application 请求
  -> Runtime / Application 调用
  -> Events 转发
  -> Result 序列化
  -> Error 映射
```

同一业务增加 CLI、HTTP 或 SDK 时，不复制业务 Workflow。

#### Observability

观测能力通过 Events、Hooks 和 Adapter 接入：

- 不修改 Core Result 语义。
- 不把 Trace 当作 Memory 或 Workflow State。
- 至少记录 run_id、component、event、duration、usage 和 error。

#### Evals

Evals 分两层：

1. Kernel Evals：验证协议、运行链路、错误和真实模型行为。
2. Application Evals：验证业务答案、证据、规则和用户目标。

### 7.7 生产化演进路径

Kernel 稳定后的演进顺序：

```text
单进程 Runtime
  -> 持久化 Workflow State
  -> 可替换 Memory Store
  -> 远程 Runtime Adapter
  -> 多租户和权限隔离
  -> 分布式调度
```

每一步都必须先升级架构版本，不直接在旧版本文档上覆盖。

### 7.8 暂不规划的平台化能力

以下能力等 Kernel、真实模型闭环和第一个业务 Application 稳定后再评估：

- Agent Registry。
- Workflow Registry。
- Tool Catalog。
- 可视化管理平台。
- 远程运行服务。
- 多租户和分布式调度。
- 自动化 Agent 发现和动态编排。

---

## 8. 模块确认记录

### 8.1 Kernel 总体边界

状态：已确认。

确认内容：

```text
采用 Agent / Workflow / Tool / Memory / Model / Runtime 六个核心原语。
核心优先，暂不兼容旧业务逻辑。
业务全部放入独立 applications/。
后续避免创造平行名词。
```

确认提交：

```text
fa4133c docs(架构): 确认 Agent Kernel 六原语边界
```

### 8.2 Execution 执行层

状态：已确认。

确认内容：

```text
Execution 不是新的核心原语。
Retry、Cancellation、Streaming 统一属于运行层。
Context、Hooks、Guardrails 只作为运行支撑能力存在。
Agent 保持无状态，Runtime 负责生命周期。
```

### 8.3 Agent

状态：已确认。

确认内容：

```text
Agent 是独立的智能执行单元。
Agent 组合 Instructions、Model、Tools 和 Memory。
Agent 不负责 Workflow 调度、存储、UI、业务状态或运行生命周期。
Agent 由 Runtime / Execution 调用和治理。
```

### 8.4 Tool

状态：已确认。

确认内容：

```text
Tool 是明确、结构化、可治理的外部动作。
Tool 负责输入校验、外部执行、结构化输出和明确错误。
Tool 不负责推理、Workflow 路由、Prompt、共享状态或业务流程。
权限、超时、取消、幂等和 Trace 由 Execution 治理。
```

### 8.5 Workflow

状态：已确认。

确认内容：

```text
Workflow 是确定性的流程组合单元。
Workflow 连接 Agent、Tool 和函数步骤。
Workflow 负责顺序、分支、暂停、恢复和流程结果。
Workflow 不替代 Agent，不实现 Tool，不管理 Memory 存储或业务状态。
```

### 8.6 Memory

状态：已确认。

确认内容：

```text
Memory 负责跨运行保存和读取 Agent 上下文。
对话记忆、工作记忆和语义检索记忆属于 Memory 的使用方式。
Memory 不负责 Workflow 状态、Trace、UI 历史或业务数据库。
Memory 通过 Adapter 连接具体存储。
```

### 8.7 Model

状态：已确认。

确认内容：

```text
Model 是与具体 Provider 无关的模型调用能力。
Model 负责请求、响应、Tool Call 意图、usage 和模型错误。
Model 不负责 Prompt、Memory、Tool 执行、Workflow 路由或业务规则。
Agent 只依赖 Model 协议，不依赖具体 Provider SDK。
```

### 8.8 Runtime

状态：已确认。

确认内容：

```text
Runtime 负责 Agent / Workflow 的完整运行生命周期。
Runtime 协调 Execution，处理开始、执行、暂停、恢复、取消和结束。
Runtime 不负责 Agent 推理、Workflow 业务流程、Tool 实现或 Memory 存储。
具体 Runtime 只能通过 Adapter 接入，不能泄漏框架状态。
```

### 8.9 支撑协议

状态：已确认。

确认内容：

```text
Context 只描述当前运行。
Events 只描述运行过程。
Errors 统一失败和终止语义。
Agent、Tool、Workflow、Runtime 分别定义自己的结构化结果。
不创建万能结果对象或新的核心原语。
```

只在六个原语的边界确认后补充必要内容，不单独扩张为新的核心抽象。

### 8.10 Applications

状态：已确认。

确认内容：

```text
Application 负责组合 Kernel 能力完成具体业务。
业务 Prompt、规则、数据模型、业务 Tool 和业务 Workflow 都属于 Application。
Application 不修改 Kernel，不反向污染 Core，不复制一套框架。
Interface 只能通过 Application 使用业务能力。
```

只描述业务如何组合 Kernel，不在 Kernel 中增加业务概念。

### 8.11 Interfaces

状态：已确认。

确认内容：

```text
Interface 是用户或外部系统访问 Application 的入口。
Interface 负责输入转换、Application 调用、事件转发、结果序列化和错误映射。
Interface 不负责 Agent、Workflow、Tool、Memory、Model 或业务规则。
Interface 不能绕过 Application 直接拼装 Kernel。
```

CLI、TUI、HTTP 等入口最后迁移，不反向决定 Kernel 的设计。

### 8.12 模块确认记录模板

后续新增或修改模块必须按以下结构记录：

| 字段 | 必须回答的问题 |
|---|---|
| 目标 | 这个模块为用户或系统提供什么能力？ |
| 输入 | 接收哪些结构化数据和运行上下文？ |
| 输出 | 返回什么结果、事件和 usage？ |
| 核心职责 | 模块自己做什么？ |
| 非职责 | 明确不做什么，防止边界漂移 |
| 依赖 | 依赖哪些 Core Protocol 或 Adapter？ |
| 生命周期 | 如何开始、暂停、恢复、取消和结束？ |
| 错误 | 错误类别、是否可重试、是否终止 |
| 可替换点 | 替换实现时公共协议是否保持不变？ |
| 测试 | 对应哪些 Unit、Contract、Integration 或 E2E？ |
| 证据 | 用什么文件、事件、日志或测试结果证明完成？ |

### 8.13 实现准入门禁

模块只有同时满足以下条件，才允许创建代码目录：

1. 模块边界已确认。
2. 最小输入、输出和错误已写入规格。
3. 至少关联一个验收 ID。
4. 已明确是否需要真实 Model Integration。
5. 已说明对其他文档和版本的影响。

---

## 9. 开发规格维护与版本化

### 9.1 单一完整规格

`DEV_SPEC.md` 是当前开发规格的完整入口，持续维护当前已经确认的：

- 项目目标和范围。
- 核心原语和模块边界。
- 技术选型原则。
- 测试和验收口径。
- 任务排期和阶段门禁。
- 已确认的模块设计。
- 文档和版本维护规则。

新增功能或确认模块后，必须先更新本文件，使本文件始终能独立说明当前开发规格。不能只把设计写在任务计划、聊天记录或单个模块文档中。

### 9.2 版本增量文档

当完成一个设计/架构里程碑，或新增功能形成独立可审计变更时，在 `docs/dev-spec/versions/` 增加一份版本增量文档：

```text
docs/
  dev-spec/
    README.md
    versions/
      v<版本号>-<主题>.md
```

版本增量文档用于回答：

- 这个版本新增了什么。
- 这个版本修改了什么。
- 为什么需要这次变更。
- 相对哪个版本变化。
- 影响哪些模块、任务、接口和测试。
- 如何迁移，哪些内容不兼容。
- 当前有哪些限制。

版本增量文档不是 `DEV_SPEC.md` 的替代品，也不重复复制整份开发规格。它只记录该版本新增和变化的内容，便于按版本回顾。

### 9.3 何时需要新增版本文档

模块逐项确认如果仍属于同一个设计里程碑，只更新 `DEV_SPEC.md` 和设计确认记录，不为每个模块单独创建版本文件。

以下变化需要新增版本增量文档：

| 变化类型 | `DEV_SPEC.md` | `docs/dev-spec/versions/` | 架构版本 |
|---|---|---|---|
| 修正错别字、失效链接或不改变语义的表达 | 更新 | 不需要 | 不需要 |
| 同一设计里程碑内的模块确认 | 更新 | 不需要 | 不需要 |
| 新增不改变核心边界的独立功能 | 更新 | 新增 | 按影响决定 |
| 改变原语职责、依赖方向或运行链路 | 更新 | 新增 | 必须新增 |
| 新增业务 Application | 更新 | 新增 | 按是否改变系统边界决定 |
| 新增外部接口、持久化模型或部署方式 | 更新 | 新增 | 必须新增 |

只要变化会影响架构事实源，就必须同时遵守架构版本规则，不能只更新 `DEV_SPEC.md`。

### 9.4 版本增量文档模板

每份版本增量文档必须包含：

1. 版本信息。
2. 基线版本。
3. 变更原因。
4. 新增内容。
5. 修改内容。
6. 受影响模块。
7. 依赖和兼容性。
8. 迁移策略。
9. 测试和验收标准。
10. 对应架构版本、主题分册和实施计划。
11. 已知限制。

### 9.5 一次变更的同步顺序

```text
确认需求
  -> 更新 DEV_SPEC.md
  -> 判断是否需要开发规格版本文档
  -> 判断是否需要架构新版本
  -> 更新主题分册和架构 changelog
  -> 创建版本化实施计划
  -> 实现和验证
  -> 在版本文档补齐实际结果
```

开发规格、架构版本和实施计划之间必须互相链接，不能出现只更新其中一份文档的情况。

### 9.6 已发布文档的只读规则

- 已发布的架构版本正文不得原地覆盖。
- 已发布的开发规格版本增量文档不得重写为新版本内容。
- 当前完整规格只能维护在根目录 `DEV_SPEC.md`。
- 历史版本只允许追加归档、替代版本和实际结果元信息。

### 9.7 当前开发规格版本记录

| 日期 | 开发规格版本 | 架构基线 | 变更摘要 | 状态 |
|---|---|---|---|---|
| 2026-07-12 | v0.15 | DEV_SPEC v0.4 | 完成对抗性审查修订：补齐外围能力归属、Prompt 所有权、契约矩阵、真实模型纵向切片、验收矩阵和任务拆解，并合并模块版本碎片；明确不使用模拟模型 | 已建立基线 |
| 2026-07-12 | v0.16 | DEV_SPEC v0.15 | 按参考规格的详细小节结构重写第 1-7 章，补充第 8-10 章的确认模板、准入门禁和阅读顺序；前置真实模型 Smoke，细化模块契约、测试分层、扩展路径和阶段进度 | 待用户审查 |

---

## 10. 当前文档索引

| 文档 | 作用 | 是否可覆盖 |
|---|---|---|
| `DEV_SPEC.md` | 当前完整开发规格 | 可以持续更新 |
| `docs/dev-spec/README.md` | 开发规格版本目录入口和编写规则 | 可以持续更新 |
| `docs/dev-spec/versions/` | 各版本新增和变更的开发规格记录 | 已发布文档只读 |
| `docs/architecture/README.md` | 新架构版本规则入口 | 可以持续更新 |
| `docs/architecture/versions/` | 新架构版本完整正文 | 已发布正文只读 |
| `docs/superpowers/specs/` | 模块和阶段确认记录 | 当前设计阶段持续追加 |
| `docs/superpowers/plans/` | 后续实现计划目录 | 实现阶段按需创建 |

## 文档使用规则

1. `DEV_SPEC.md` 负责描述开发规格的主线和章节组织。
2. `DEV_SPEC.md` 同时维护当前完整开发规格，不把当前内容拆散到多个平行入口。
3. 版本新增和变更记录放在 `docs/dev-spec/versions/`，具体模块确认记录放在 `docs/superpowers/specs/`。
4. 当前新项目设计事实以 `DEV_SPEC.md` 和已确认的 `docs/superpowers/specs/` 为准。
5. 第一个 Kernel 版本确认后，创建新的 `docs/architecture/versions/` 完整架构正文。
6. 后续任何改变系统边界的设计，在进入实现前必须创建新的架构版本文档。
7. 本文件只记录已确认的边界；未确认内容必须明确标记为“待确认”。

## 阅读顺序

第一次进入项目时按以下顺序阅读：

1. 第 1 章：理解项目目标、边界和非目标。
2. 第 2 章：理解六个 Core、Execution 和外围能力。
3. 第 3 章：理解协议、Adapter、真实模型和配置。
4. 第 4 章：理解测试层级和真实模型验收。
5. 第 5 章：理解架构图、模块输入输出和运行链路。
6. 第 6 章：理解当前阶段、任务和门禁。
7. 第 8 章：查看已经确认的模块记录。
8. 第 9 章：修改规格或新增版本前先阅读维护规则。
