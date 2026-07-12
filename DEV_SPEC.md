# Agent Kernel Developer Specification

> 版本：0.15 — Agent Kernel 完整设计规格基线
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

#### 核心优先

先稳定通用 Agent 能力，再建立业务应用。第一阶段不迁移旧工伤业务，也不保留旧业务协议兼容层。

#### 少量原语

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

#### 组合优于继承

Agent 组合 Model、Tool 和 Memory；Workflow 组合 Agent、Tool 和步骤；Application 组合 Kernel 能力完成业务。

#### 依赖方向单一

Kernel 不依赖业务。业务、接口和适配器依赖 Kernel 的公开协议。

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

---

## 3. 技术选型

### 3.1 选型原则

技术选型服从 Kernel 边界，而不是反过来让某个框架决定 Kernel：

- Python 3.11。
- 使用 `uv` 管理环境、依赖和命令。
- 使用异步边界承载模型、工具、记忆和运行时调用。
- 优先选择轻量、可替换、易测试的实现。
- 不在 Kernel 公共协议中暴露第三方 SDK 类型。

### 3.2 Kernel 与 Adapter

Kernel 只定义稳定协议，Adapter 负责连接具体技术：

```text
Kernel Protocol
  -> Model Adapter
  -> Memory Adapter
  -> Runtime Adapter
  -> Tool Adapter
```

Adapter 可以替换具体库、服务或存储，但不能把供应商概念泄漏到 Kernel。

### 3.3 Runtime 选择

Runtime 的具体实现暂按以下顺序处理：

先实现一个最小 Runtime 验证 Kernel 语义，再通过 Adapter 接入其他工作流运行时。任何具体运行时都不能进入 Agent、Tool、Workflow、Memory 或 Model 的公共协议。

### 3.4 暂不提前决定的内容

在模块逐项确认前，不提前冻结：

- 生产环境的 Model Provider 组合和多 Provider 路由策略；第一条纵向切片使用当前真实模型配置。
- 具体 Memory 存储。
- 具体 Tool 注册方式。
- 具体 Workflow 编排库。
- 具体 Trace 存储。
- 具体 CLI、TUI 或 HTTP 框架。

### 3.5 第一条纵向切片的实现基线

为了让规格可以直接驱动第一轮实现，第一条纵向切片固定采用最小实现：

| 能力 | 第一阶段选择 | 替换边界 |
|---|---|---|
| Model | 真实 Model Provider Adapter；通过 `ANANHU_REAL_MODEL` 选择，当前配置为 `doubao-seed-2-0-mini-260428` | Model Protocol |
| Memory | In-memory Adapter | Memory Protocol |
| Tool | 一个无副作用结构化 Tool | Tool Protocol |
| Runtime | 单进程本地 Runtime | Runtime Protocol |
| Interface | 程序化测试入口 | Interface Protocol |
| Observability | 内存事件收集器 | Events / Trace Adapter |

真实模型是第一条纵向切片的必选依赖；`In-memory Memory` 和无副作用 Tool 只用于缩小验证范围，不代表模型调用可以被模拟。Provider 仍通过 Adapter 接入，不进入 Kernel 公共协议。

### 3.6 真实模型测试规则

- 真实模型测试必须实际发起 Provider 调用，不允许模拟模型、固定文本替身或静默降级。
- `ANANHU_REAL_MODEL` 固定本轮测试使用的模型标识，运行结果必须记录模型标识、usage、延迟、请求结果和错误分类。
- `ANANHU_REAL_MODEL_SMOKE=1` 才允许执行需要网络和凭证的真实模型 Smoke / Integration 测试；未开启时测试必须明确报告未执行原因。
- 凭证、Provider 配置或网络不可用时，真实模型测试必须失败或标记为阻塞，不能改用模拟模型伪造通过。
- 断言优先检查结构化结果、Tool Call、事件顺序、usage、错误语义和取消传播，不对自然语言具体措辞做脆弱的全文匹配。
- 真实模型测试使用固定、低成本、可重复的输入，并设置超时、重试上限和费用边界。

---

## 4. 测试方案

### 4.1 测试目标

测试首先证明 Kernel 的语义稳定，再证明不同 Adapter 能够实现相同语义，最后才验证业务应用是否正确组合 Kernel。

### 4.2 Kernel 单元测试

分别验证：

```text
Agent
Workflow
Tool
Memory
Model
Runtime
```

Kernel 纯协议和边界测试不得依赖工伤业务或具体界面；Agent、Model、Tool Call、Streaming 和第一条纵向切片必须通过真实 Model Adapter 做集成验收，不允许用模拟模型替代。

### 4.3 Adapter Contract Test

所有 Adapter 通过同一份 Kernel contract：

```text
不同 Model Adapter
不同 Memory Adapter
不同 Runtime Adapter
不同 Tool Backend
```

Contract Test 关注行为一致性，不关注内部实现方式。

### 4.4 组合测试

验证 Kernel 原语组合后的基本语义：

- Agent 调用 Model、Tool 和 Memory。
- Workflow 调度 Agent、Tool 和步骤。
- Runtime 执行、暂停、恢复、取消和失败。
- 运行结果和运行过程保持可追踪。

### 4.5 架构测试

自动检查以下约束：

- `core/` 不导入 `applications/`。
- `core/` 不导入具体工作流运行时。
- `core/` 不导入具体 Provider SDK。
- `core/` 不导入 CLI、TUI 或 HTTP 框架。
- Application 只能依赖 Kernel 公开协议。
- 旧聚合协议不成为新 Kernel 的共享入口。

### 4.6 业务验收

业务 Eval 在 `applications/` 建立后单独维护，不反向污染 Kernel 测试。

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

### 5.1 总体分层

```text
Interface
  -> Application
      -> Workflow
          -> Agent
              -> Model
              -> Tool
              -> Memory
      -> Runtime

Adapter
  -> 实现 Kernel 协议
```

依赖方向保持为：

```text
Interface / Application / Adapter
  -> Kernel
```

Kernel 不反向依赖上层。

### 5.2 目标目录

目录只表达层次，不提前表达业务名词：

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
      model/
      memory/
      runtime/
      tool/
  applications/
  interfaces/
```

后续是否拆分更多文件，必须以职责边界为依据，不以“看起来完整”为依据。

### 5.3 模块设计方式

六个 Core 原语按以下字段确认：

1. 模块目标。
2. 核心职责。
3. 非职责。
4. 最小公开契约。
5. 依赖关系和生命周期。
6. 可替换点和错误边界。
7. 测试和验收标准。
8. 用户确认记录。

Execution、支撑协议、Applications 和 Interfaces 使用层级说明，不强行套用 Core 原语模板。

只有完成确认并关联验收 ID 的内容，才允许进入实现计划。

### 5.4 模块确认顺序

```text
Execution
  -> 已确认运行层边界
Agent
  -> 已确认智能执行单元边界
Tool
  -> 已确认结构化外部动作边界
Workflow
  -> 已确认流程组合边界
Memory
  -> 已确认跨运行上下文边界
Model
  -> 已确认 Provider 无关模型调用边界
Runtime
  -> 已确认运行生命周期边界
支撑协议
  -> 已确认 Context / Events / Errors / Core Result 边界
Applications
  -> 已确认业务组合边界
Interfaces
  -> 已确认接口边界
```

支撑协议只能服务六个原语，不能再次形成新的核心层。

### 5.5 运行链路说明方式

后续每个模块都必须同时说明两条链路：

#### 配置链路

```text
Application
  -> 组装 Agent / Workflow / Tool / Memory / Model
  -> 交给 Runtime
```

#### 执行链路

```text
Interface
  -> Runtime
  -> Workflow 或 Agent
  -> Model / Tool / Memory
  -> 结构化结果
```

这样文档既能说明“系统由什么组成”，也能说明“请求实际如何运行”。

### 5.6 当前禁止提前创建的概念

除六个 Core 原语外，不创建或冻结以下平行核心名词：

```text
Orchestrator
Capability
Stage
Domain Core
Agent Context
```

如果未来确实需要这些名称，必须先说明它们为什么不能由现有六个原语表达，并记录确认结果。

### 5.7 Execution 运行规则

一次 Agent 运行统一遵循：

```text
Runtime 创建运行
  -> Context 初始化
  -> Agent 读取 Memory
  -> Model 生成
  -> Tool 执行（可选）
  -> Model 继续生成
  -> Streaming 输出过程
  -> 返回结构化结果
```

运行失败时由 Execution 层统一判断是否 Retry；用户或系统要求停止时进入 Cancellation；二者不能混用。

### 5.8 Core Contract Matrix

| 原语 | 最小输入 | 最小输出 | 主要错误 | 生命周期 | 替换点 |
|---|---|---|---|---|---|
| Agent | input、Instructions、Tools、Memory | output、tool_calls、usage、stop_reason | model、tool、policy、internal | run -> complete / fail / cancel | Agent 配置 |
| Workflow | workflow input、steps、条件 | step_results、output、stop_reason | step、branch、pause、resume | start -> step -> pause / finish | Workflow 实现 |
| Tool | 结构化 input、Execution Context | 结构化 output | validation、permission、timeout、execution | validate -> execute -> result | Tool Adapter |
| Memory | read / write / search 请求 | context items / write result | scope、storage、serialization | read / write / query | Memory Adapter |
| Model | Model Request | response、tool_call、usage | provider、timeout、format | request -> response / error | Model Adapter |
| Runtime | Run Request、Agent 或 Workflow | events、Runtime Result | runtime、cancel、timeout、internal | start -> execute -> pause / resume -> finish | Runtime Adapter |

这张表是实现前的最小契约，具体字段 schema、序列化格式和错误码在实现计划中冻结；实现不得绕过表中的替换点直接依赖具体基础设施。

### 5.9 第一条纵向切片

第一条可运行路径固定为：

```text
Programmatic Interface
  -> Application Fixture
      -> Runtime
          -> Execution
              -> Agent
                  -> Real Model Provider Adapter
                  -> In-memory Memory
                  -> No-side-effect Tool
              -> Events
          -> Agent Result
```

纵向切片必须完成一次 Model 生成、一次可选 Tool Call、一次 Memory 写入和一次结构化结果返回，并覆盖成功、Tool 输入错误、取消和流式事件四类结果。

---

## 6. 项目排期

### 6.1 阶段总览

| 阶段 | 目标 | 产出 | 状态 |
|---|---|---|---|
| 0 | 清理旧项目并建立新分支 | 新 Kernel 文档基线 | 已完成 |
| 1 | 确认 Core、Execution、支撑协议和外围边界 | `DEV_SPEC v0.15`、契约矩阵、验收矩阵 | 已完成 |
| 2 | 实现第一条真实模型 Kernel 纵向切片 | Real Model Adapter、In-memory Memory、Tool、Agent、Runtime、Events | 待开始 |
| 3 | 补齐 Kernel Contract Tests | 六原语和 Adapter 合同测试 | 待开始 |
| 4 | 建立第一个架构版本 | 完整架构正文、迁移/兼容说明、版本索引 | 待开始 |
| 5 | 组合业务 Application | `applications/<业务>/` | 待开始 |
| 6 | 接入 Interfaces、Observability 和 Evals | CLI / API / Trace / Eval | 待开始 |

### 6.2 阶段门禁

每个阶段必须满足前一阶段的验收条件：

```text
文档结构确认
  -> 契约和验收确认
  -> 第一条纵向切片计划
  -> Kernel 纵向切片
  -> Contract Tests
  -> 第一个架构版本
  -> Application
  -> Interfaces / Observability / Evals
```

在用户确认完整设计前，不进入代码实现。

### 6.3 任务记录

| 任务 ID | 任务 | 依赖 | 输出 | 验收 |
|---|---|---|---|---|
| K-01 | 建立 `src/agent_kernel/` 最小协议目录 | 规格审查通过 | 六原语最小协议 | K-009 |
| K-02 | 接入真实 Model Adapter，配置 In-memory Memory 和无副作用 Tool | K-01 | 真实模型 Adapter、Memory Adapter、Tool Adapter | K-001、K-003、K-006、K-007 |
| K-03 | 实现 Agent 单次执行闭环 | K-02 | Agent + Tool Call 循环 | K-001、K-002 |
| K-04 | 实现最小 Runtime 和 Events | K-03 | start / execute / cancel / finish | K-008 |
| K-05 | 实现最小 Workflow 顺序、分支、暂停恢复 | K-04 | Workflow 运行协议 | K-004、K-005 |
| K-06 | 建立 Kernel Contract Tests 和真实模型纵向切片 | K-01-K-05 | 自动化验收证据、真实调用记录 | K-010 |
| K-07 | 创建第一个完整架构版本 | K-06 | `docs/architecture/versions/` 版本正文 | 架构版本验收 |

每个任务必须记录基线规格、修改边界、关联验收 ID、验证命令和结果；没有这些信息不得标记完成。

---

## 7. 可扩展性与未来展望

### 7.1 新增业务

新增业务只新增 Application：

```text
applications/
  work_injury/
  customer_service/
  legal_consultation/
```

不同业务不复制 Kernel，也不把业务模型写回 Kernel。

### 7.2 新增 Agent

只有当任务具备独立目标、Instructions、Tool 集合、Memory 策略、输出边界和测试边界时，才新增 Agent。

“多 Agent”不是架构目标，清晰的职责边界才是。

### 7.3 新增 Tool

每个 Tool 应当只有一个明确动作，并具备：

```text
结构化输入
结构化输出
明确错误
明确权限
可测试行为
```

### 7.4 新增 Runtime 或 Provider

新增 Runtime 或 Provider 只能实现既有 Kernel 协议，不得复制一套业务流程或平行状态模型。

### 7.5 暂不规划的平台化能力

以下能力等 Kernel 稳定后再评估：

- Agent Registry。
- Workflow Registry。
- Tool Catalog。
- 远程运行服务。
- 可视化管理平台。
- 多租户和分布式调度。

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
| 2026-07-12 | v0.15 | DEV_SPEC v0.4 | 完成对抗性审查修订：补齐外围能力归属、Prompt 所有权、契约矩阵、真实模型纵向切片、验收矩阵和任务拆解，并合并模块版本碎片；明确不使用模拟模型 | 待用户审查 |

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
