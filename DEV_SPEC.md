# Agent Kernel Developer Specification

> 版本：0.25 — 从 Agent Kernel 到完整 Agent 系统的演进基线
>
> 状态：第一至七章已确认；第一阶段仍止于通用 Kernel，Agent Harness、业务 Application 和 Multi-Agent 属于后续证据驱动的演进路线
>
> 当前架构主分支：`architecture`
>
> 文档目的：冻结当前完整设计、跨模块契约、验收口径和实现顺序；本文件不包含具体实现代码。

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 核心特点](#2-核心特点)
- [3. 技术选型](#3-技术选型)
- [4. 测试与验收](#4-测试与验收)
- [5. 系统架构与模块设计](#5-系统架构与模块设计)
- [6. 项目排期](#6-项目排期)
- [7. 从 Agent Kernel 到完整 Agent 系统](#7-从-agent-kernel-到完整-agent-系统)

---

## 1. 项目概述

本项目通过从零设计和实现一个通用 Agent Kernel，系统学习 Agent 框架的核心原理、模块边界与工程化方法。

项目以真实可运行的工程实现承载学习过程。每个核心模块都需要依次完成职责分析、边界确认、公共契约设计、代码实现和真实链路验证，最终形成一个简洁、通用、可组合、可测试的 Agent Kernel。

### 1.1 项目定位

> **核心定位：通过实现理解 Agent 框架**

本项目首先是一个 Agent 框架学习项目，其次是一套可复用的工程成果。

学习不以阅读概念、拼装第三方框架或展示功能数量为完成标准，而是通过亲手设计和实现 Agent Kernel，回答以下核心问题：

- Agent 如何组织模型、工具、记忆和指令。
- Workflow 如何描述多步骤执行、分支和暂停恢复。
- Tool 如何被声明、调用、治理并返回结果。
- Memory 如何写入、检索并参与后续执行。
- Model 如何通过统一协议接入不同 Provider。
- Runtime 如何驱动执行、流式输出、取消和事件传播。

最终产物不是某个具体业务 Agent，而是能够被不同业务应用组合使用的通用 Kernel。

### 1.2 学习目标

本项目需要完成三层学习目标：

| 层次 | 学习目标 | 验证方式 |
|---|---|---|
| 概念理解 | 理解 Agent 框架的核心原语及职责边界 | 能独立说明每个模块负责什么、不负责什么 |
| 架构设计 | 理解模块组合、依赖方向和适配器隔离 | 能通过公开契约替换模型、存储或运行时实现 |
| 工程实现 | 掌握测试、可观测性、错误处理和真实链路验收 | 能运行真实模型对话并获得可检查的执行证据 |

学习结果必须通过设计文档、公共契约、可运行代码和测试证据共同体现，不能只以文档理解或功能演示代替。

### 1.3 为什么从零实现

直接使用成熟 Agent 框架可以快速构建应用，但会隐藏执行循环、状态传递、工具调用、记忆接入和运行时调度等关键机制。

本项目选择从空白起点实现最小 Agent Kernel，目的是：

- 观察一次 Agent 执行从输入到结果的完整过程。
- 理解各模块之间真正需要传递的数据和协议。
- 区分核心能力、适配器能力与业务能力。
- 通过替换具体实现验证抽象是否成立。
- 通过失败路径和真实运行发现仅阅读源码难以暴露的问题。

旧项目完整保留在 `mvp` 和 `main`。当前重构分支不读取、不兼容、不迁移旧代码、旧文档、旧计划、旧业务协议或旧入口，避免历史实现影响新的学习和设计判断。

### 1.4 核心设计理念

本项目遵循以下设计理念：

| 设计理念 | 核心含义 |
|---|---|
| 实现驱动学习 | 每个概念都需要落实为可运行代码和可检查行为 |
| 少量核心原语 | 使用少量稳定概念建立完整、清晰的框架心智模型 |
| 组合优于继承 | Agent、Workflow 和 Application 通过组合获得能力 |
| 单向依赖 | 业务、接口和适配器依赖 Kernel，Kernel 不反向依赖外围实现 |
| 真实链路验证 | 模型相关能力必须通过真实 Provider 和真实对话验证 |
| 文档即工程契约 | 已确认的设计、代码实现、测试和验收结果必须保持一致 |

核心只保留六个原语：

```text
Agent
Workflow
Tool
Memory
Model
Runtime
```

其他概念只能作为支撑协议、适配器或实现细节存在。新增核心概念前，必须证明现有六个原语无法清晰表达对应职责。

### 1.5 当前范围

当前阶段覆盖：

- 六个核心原语的职责、边界和协作关系。
- Kernel、Adapter、Application 和 Interface 的依赖关系。
- Agent 从输入到结果的最小执行链路。
- Tool Call、Memory、Streaming、Cancellation 和 Execution Events。
- 公共契约、错误语义和可观测结果。
- 模块级测试、契约测试、集成测试与真实对话验收。
- 逐模块确认、实现和累计验收的开发方式。

当前阶段不覆盖：

- 工伤业务规则和业务数据模型。
- RAG、MCP、向量数据库、知识库和政策检索实现。
- 具体业务 Prompt 和业务数据协议。
- 生产级多租户、分布式调度和远程 Runtime。
- 完整 CLI、TUI、HTTP 或 Web Dashboard。
- 以功能数量或多 Agent 数量作为学习成果。

业务应用以后统一放在 `applications/`，只能通过公开契约组合 Kernel 能力，不能把业务概念反向引入 Kernel。

### 1.6 阶段成果

第一阶段完成后，应当得到一个能够支持最小真实 Agent 对话的 Kernel，并形成以下可观察成果：

| 成果 | 可观察结果 |
|---|---|
| 可运行 | 真实 Model、Agent、Tool、Memory 和 Runtime 能够形成执行闭环 |
| 可理解 | 每个核心模块都有明确职责、边界、输入、输出和错误语义 |
| 可组合 | Agent、Workflow、Tool 和 Application 能够通过公开契约组合 |
| 可替换 | Model、Memory、Tool 和 Runtime 的具体实现可以通过适配器替换 |
| 可解释 | 执行事件、结果、usage、延迟和错误能够被追踪 |
| 可验证 | 每个模块都有自动化测试和累计真实对话证据 |

第一阶段不是以目录创建、接口声明或单元测试通过作为完成标志。只有已经确认的模块完成实现，并在累计真实对话链路中承担预期职责，才能视为学习和实现完成。

---

## 2. 核心特点

本章概述 Agent Kernel 最重要的设计特点，说明每项特点解决的工程问题以及对应的学习价值。

具体模块职责、公共契约和依赖规则在第五章展开；测试场景和验收门禁在第四章展开，本章不重复实现级细节。

### 2.1 六个原语建立最小心智模型

Kernel 只保留六个核心原语：

```text
Agent
Workflow
Tool
Memory
Model
Runtime
```

每个原语只承担一种主要职责：

| 原语 | 核心职责 | 需要理解的问题 |
|---|---|---|
| `Agent` | 组合 Model、Tool、Memory 和 Instructions 完成智能任务 | 一个 Agent 如何从输入得到结果 |
| `Workflow` | 组合多个步骤并控制执行顺序 | 多步骤任务如何分支、暂停和恢复 |
| `Tool` | 以结构化方式调用外部能力 | 模型意图如何转化为可治理动作 |
| `Memory` | 跨运行保存和读取上下文 | 上下文如何被写入、隔离和召回 |
| `Model` | 提供与 Provider 无关的模型生成能力 | 如何隔离模型协议与供应商实现 |
| `Runtime` | 驱动 Agent 或 Workflow 的运行生命周期 | 一次运行如何开始、执行和结束 |

六个原语共同建立 Agent 框架的最小心智模型。Context、Events、Errors、Hooks、Guardrails、Retry、Cancellation 和 Streaming 等能力只作为运行支撑协议存在，不扩张为新的核心原语。

### 2.2 从输入到结果的完整执行闭环

Kernel 不把 Agent 理解为一次简单的模型调用，而是关注从输入到结构化结果的完整执行过程。

最小 Agent 链路为：

```text
用户输入
  -> Runtime 创建运行
  -> Agent 组装任务上下文
  -> Memory 读取相关上下文
  -> Model 生成响应或 Tool Call
  -> Tool 执行结构化动作
  -> Model 根据 Tool Result 继续生成
  -> Memory 写入需要保留的上下文
  -> Runtime 返回 Result 和 Events
```

Workflow 在此基础上组合多个 Agent、Tool 或函数步骤：

```text
Runtime
  -> Workflow
      -> Agent / Tool / Function Step
      -> 顺序 / 分支 / 并行
      -> 暂停 / 恢复
      -> Workflow Result
```

Execution 为整个过程提供 Context、Hooks、Guardrails、Retry、Cancellation 和 Streaming，但它不是第七个核心原语。

通过实现这条链路，可以观察模型生成、工具调用、记忆读写和运行治理如何协同，而不是只看到最终自然语言答案。

### 2.3 组合式架构与单向依赖

Kernel 通过组合获得能力，不通过继承或业务特例修改核心行为。

```text
Agent
  = Instructions + Model + Tool + Memory

Workflow
  = Agent / Tool / Function Step 的流程组合

Application
  = 业务配置 + Kernel 原语组合
```

依赖方向保持单一：

```text
Interface
  -> Application
      -> Kernel

Adapter
  -> Kernel Protocol
```

Kernel 不依赖具体业务、外部 Interface、Provider SDK 或具体存储。业务能力只能在 Application 中组合 Kernel，不能反向进入核心模块。

这种设计用于学习两个重要问题：

- 如何通过组合建立复杂能力。
- 如何使用单向依赖保护稳定的核心边界。

### 2.4 Adapter 驱动的全链路可替换

第三方模型、存储、外部工具和运行时只能通过 Adapter 接入 Kernel：

| 可替换实现 | Kernel 保持稳定的内容 |
|---|---|
| Model Provider | Model Request、Response、Tool Call 和错误语义 |
| Memory Store | Memory 的读取、写入、搜索和作用域语义 |
| Tool Backend | Tool 输入、输出、错误和执行语义 |
| Runtime Engine | 生命周期、事件、取消和最终结果语义 |

例如，更换 Model Provider 时，Agent 仍然只依赖 Model 公共协议；更换 Memory Store 时，Agent 和 Workflow 不需要理解数据库类型或存储格式。

可替换不是为了提前支持所有供应商，而是用于验证：

> 公共协议是否真正描述了能力，而不是泄漏某个具体实现。

第一阶段只实现打通真实链路所需的最小 Adapter，不提前建设完整 Provider 生态。

### 2.5 结构化结果与可解释运行过程

Agent Kernel 不只返回最终文本，还要提供可检查的结构化结果和运行事件。

一次运行至少需要回答：

- 哪个 Agent 或 Workflow 被执行。
- 使用了哪个 Model。
- 是否读取或写入了 Memory。
- 是否产生并执行了 Tool Call。
- 当前运行是完成、失败、暂停还是取消。
- 每一步产生了哪些事件、usage、延迟和错误。
- 最终 Result 与运行事件是否属于同一个 run。

运行证据采用结构化 Events 和各模块自己的 Result 表达，不依赖拼接日志，也不创建一个包含所有字段的万能结果对象。

这种设计让 Streaming、Trace、测试、评估和外部 Interface 可以共享同一套运行事实，也帮助学习者观察 Agent 框架内部真实发生了什么。

### 2.6 渐进式真实对话验证

每个模块都必须在真实用户输入驱动的累计链路中完成验证。

实施过程不是先孤立实现所有模块，再在最后一次性组装，而是让真实链路逐步增长：

```text
真实 Model
  -> Agent
  -> Tool
  -> Memory
  -> Runtime / Execution
  -> Workflow
```

每完成一个模块，都需要：

1. 增加至少一个该模块负责的真实对话场景。
2. 验证模块产生的结构化结果、事件或状态变化。
3. 重新运行此前已经通过的真实对话场景。
4. 同时保留 Unit、Contract 和 Architecture Tests。
5. 在真实 Provider 不可用时明确标记阻塞，不使用模拟输出伪造完成。

这种方式把测试同时作为学习工具：不仅证明模块接口正确，还能观察模块在真实 Agent 链路中是否真正承担了预期职责。

具体 `RD-*` 场景、断言和失败处理规则由第四章定义。

### 2.7 从通用 Kernel 扩展到业务 Application

Kernel 只提供稳定的 Agent 能力和执行边界，不包含工伤咨询、政策检索、待遇测算或其他业务概念。

业务应用以后统一放在：

```text
applications/
```

Application 可以组合：

```text
Application
  -> 业务 Instructions 和 Prompt
  -> Agent
  -> Workflow
  -> 业务 Tool
  -> Memory 使用策略
  -> Model 和 Runtime 配置
```

Interface 只负责让用户或外部系统访问 Application，例如 CLI、TUI 或 HTTP API，不负责重新实现 Agent、Workflow 或业务规则。

从 Kernel 扩展到 Application 的过程用于验证两件事：

- Kernel 是否足够通用，可以服务不同业务。
- 业务是否能够通过组合完成，而不需要修改核心模块。

第一阶段只完成通用 Kernel。业务 Application 和外部 Interface 必须等 Kernel 边界、公共契约和真实链路通过验收后再开始。

---

## 3. 技术选型

本章说明为了学习并实现 Agent Kernel，第一阶段选择哪些技术策略、哪些能力自行实现、哪些能力复用成熟工具，以及每项选择接受什么限制。

公共协议的完整字段和模块执行流程在第五章定义；测试场景在第四章定义；实施顺序在第六章定义。本章不提前决定尚未逐模块确认的实现细节。

### 3.1 技术选型目标与判断标准

技术选择必须服务于“通过实现理解 Agent 框架”的学习目标，不能让第三方框架替代需要亲手理解的核心机制，也不能把时间消耗在与 Agent Kernel 无关的底层重复建设上。

| 判断标准 | 具体要求 |
|---|---|
| 有助于学习 | 能直接帮助理解 Agent、Workflow、Tool、Memory、Model 或 Runtime |
| 边界清晰 | 第三方类型和 SDK 不进入 Kernel 公共协议 |
| 最小可运行 | 优先打通一条真实链路，不提前建设完整平台 |
| 可以替换 | 更换 Provider、存储或 Runtime 不改变 Kernel 语义 |
| 可以观察 | 关键输入、输出、事件、usage、延迟和错误能够检查 |
| 可以验证 | 每个选择都有 Contract Test 或真实对话证据 |
| 失败透明 | 外部能力不可用时明确失败或阻塞，不静默降级 |
| 决策可延后 | 当前阶段不需要的技术不提前冻结 |

每项技术决策必须说明：

```text
要解决的问题
候选路线
当前选择
选择理由
接受的限制
替换边界
确认状态
```

### 3.2 自研与复用边界

本项目需要亲手实现 Agent 框架的核心语义，但不重复实现成熟的通用基础设施。

#### 3.2.1 必须自行设计和实现

| 能力 | 自行实现的原因 |
|---|---|
| 六个 Core Protocol | 建立 Agent 框架的最小心智模型 |
| Agent 执行循环 | 理解输入、Model、Tool、Memory 和 Result 如何协作 |
| Tool Call 循环 | 理解模型意图如何变成结构化动作并返回模型 |
| Memory 使用语义 | 理解作用域、写入、召回和来源追踪 |
| Workflow 状态推进 | 理解顺序、分支、并行、暂停和恢复 |
| Runtime 生命周期 | 理解一次运行如何开始、取消、暂停和结束 |
| Execution 支撑语义 | 理解 Context、Events、Retry、Hooks、Guardrails 和 Streaming |
| Adapter 边界 | 理解公共协议与具体技术实现如何隔离 |

第一阶段不使用成熟 Agent 框架代替这些核心行为。第三方 Agent 框架可以作为后续对照学习材料，但不能成为 Kernel 的实现基础或公共协议来源。

#### 3.2.2 应当复用成熟工具

| 能力 | 复用原因 |
|---|---|
| Provider 网络通信 | 避免重复处理认证、HTTP 和底层协议 |
| Schema 校验与序列化 | 使用经过验证的结构化数据能力 |
| 测试执行 | 使用成熟测试框架组织 Unit、Contract 和 Integration Tests |
| 环境与依赖管理 | 使用 `uv` 保证 Python 环境一致 |
| 异步调度基础 | 使用 Python 标准异步能力，不自建事件循环 |
| 数据库或外部存储客户端 | 需要持久化时使用成熟驱动 |
| HTTP、CLI 或 UI 框架 | 在 Interface 阶段按需要选择 |

具体 Provider SDK、Schema 库、持久化客户端和 Interface 框架必须在对应模块确认时选择，本章不提前冻结。

### 3.3 Python 工程与异步执行基线

#### 3.3.1 运行环境

| 项目 | 当前选择 | 状态 |
|---|---|---|
| Python | Python 3.11，通过 `.python-version` 固定 | 已确认 |
| 环境与依赖 | `uv` | 已确认 |
| 测试入口 | `uv run pytest` | 已确认 |
| 初始部署形态 | 单进程、本地运行 | 第一阶段已确认 |
| 分布式执行 | 不进入第一阶段 | 延后 |

新 Python 工程建立后，依赖安装、测试和运行统一通过 `uv`。不从旧项目的 `pyproject.toml`、`uv.lock`、代码或测试恢复实现。

#### 3.3.2 异步边界

Model、Tool、Memory 和 Runtime 可能访问网络、磁盘或外部系统，因此公共调用边界必须保留异步能力。

第一阶段使用 Python 标准异步机制表达：

```text
Model 调用
Tool 外部执行
Memory I/O
Runtime 运行
Streaming 消费
Cancellation 传播
```

异步不用于制造无意义的复杂度。纯数据转换、Schema 校验和确定性 Workflow 条件可以保持同步。

具体并发限制、任务组装方式和超时 API 在 Runtime、Execution 与 Workflow 模块确认时确定。

#### 3.3.3 类型表达

Kernel 公共协议使用 Python 类型系统表达，但具体采用 `Protocol`、ABC、dataclass 或 Schema Model，需要根据模块输入、序列化和运行时校验需求逐项确认。

选择类型工具时必须保证：

- 公共字段明确。
- Provider SDK 类型不能泄漏。
- Contract Test 可以构造输入并检查输出。
- Events、Result 和错误可以序列化。
- 类型工具不会反向决定模块职责。

### 3.4 公共协议与结构化数据策略

Kernel 模块之间只传递与具体实现无关的结构化数据。

公共协议遵循：

| 原则 | 要求 |
|---|---|
| Provider Neutral | 不出现具体 Provider SDK 类型 |
| Explicit Input | 每个模块有明确输入对象 |
| Explicit Result | Agent、Tool、Workflow 和 Runtime 分别定义结果 |
| Explicit Error | 错误类别、来源和终止语义明确 |
| Observable Events | 运行过程通过结构化 Events 表达 |
| Serializable Boundary | 跨 Adapter、暂停恢复和测试证据可以序列化 |
| No Universal Object | 不创建包含所有模块字段的万能上下文或结果对象 |

例如，Agent 依赖的是统一 Model Request 和 Model Response 语义，而不是某个 Provider 的请求类。

第五章负责确认完整字段、类型、枚举和所有权。本章只冻结结构化、可序列化和 Provider Neutral 的技术方向。

Schema 校验与序列化工具当前状态为：

```text
能力要求：已确认
Schema Model：Pydantic v2 风格 BaseModel
公共配置：frozen=True、extra="forbid"、strict=True
具体依赖版本：阶段 A4 建立 uv 工程时确认
```

### 3.5 第一阶段 Adapter 选择

第一阶段只选择足以打通真实 Agent 链路的最小实现。

| 能力 | 当前选择 | 选择理由 | 接受的限制 | 替换边界 |
|---|---|---|---|---|
| Model | 一个真实 Model Provider Adapter | 验证真实生成、结构化输出、Tool Call 和 Streaming | 暂不支持多 Provider 路由 | Model Protocol |
| Memory | In-memory Adapter | 先验证作用域、写入和召回语义 | 进程退出后数据丢失 | Memory Protocol |
| Tool | 无副作用结构化 Tool | 验证 Schema、调用循环、错误和事件 | 不代表真实业务集成 | Tool Protocol |
| Runtime | 单进程本地 Runtime | 先理解生命周期、事件和取消 | 不支持远程和分布式执行 | Runtime Protocol |
| Observability | In-memory Events Collector | 直接检查运行证据 | 不提供持久化查询和 Dashboard | Events / Hooks |
| Interface | 程序化测试入口 | 缩小第一条链路范围 | 不提供终端或网络产品入口 | Application 调用边界 |

Adapter 的依赖方向是：

```text
Model Adapter
Memory Adapter
Tool Adapter
Runtime Adapter
  -> 实现 Kernel Protocol
```

Kernel 不依赖具体 Adapter。替换 Adapter 时，必须重新运行对应 Contract Test 和累计真实对话场景。

### 3.6 配置、凭证与 Provider 隔离

配置由 Kernel 外层读取、校验并注入：

```text
环境变量或配置文件
  -> Adapter Config
  -> 配置校验
  -> 创建具体 Adapter
  -> 注入测试 Fixture 或 Application
```

配置规则：

- Provider 凭证不得写入仓库、Result、Events 或普通日志。
- Provider SDK 配置只能存在于对应 Adapter。
- Kernel 只接收已经构造完成的协议对象。
- 缺少凭证、模型不存在或能力不满足时必须在运行前失败。
- 不允许自动切换到模拟模型、固定输出或未确认的备用 Provider。
- 模型标识属于运行配置，不属于 Kernel 架构。
- 测试证据必须记录实际使用的 Provider 和模型标识。

当前配置入口保留：

```text
ANANHU_REAL_MODEL
ANANHU_REAL_MODEL_SMOKE
```

具体 Provider 客户端、端点、凭证变量和 Tool Choice、Structured Output、Streaming 能力映射，必须在 Model Adapter 确认时冻结。

### 3.7 可观测性与测试工具策略

第一阶段不建设 Dashboard 或独立观测平台，但运行过程必须产生结构化证据。

最小观测内容包括：

```text
run_id
event_type
timestamp
component
model_id
provider
tool_name
duration
usage
stop_reason
error
retry_count
```

观测策略：

- Events 表达运行事实，不依赖解析日志。
- Result 表达模块最终输出，不承担完整 Trace。
- Hooks 提供扩展入口，但不能改变核心职责。
- 测试直接检查结构化 Result、Events 和错误。
- 具体日志库、Trace 后端和持久化方案延后选择。

测试工具策略：

| 测试类型 | 第一阶段工具方向 |
|---|---|
| Unit Test | `pytest` |
| Contract Test | `pytest` + 各 Protocol 的共享合同 |
| Async Test | `pytest` 的异步测试能力，具体插件按工程建立时确认 |
| Architecture Test | AST 或导入依赖检查 |
| Integration Test | 真实 Adapter 和累计真实对话 Fixture |
| Performance Test | 需要时增加 benchmark，不作为第一阶段完成前提 |

所有测试命令统一通过 `uv run` 执行。

### 3.8 第一条纵向切片技术基线

第一条纵向切片用于证明最小技术选择能够支持真实 Agent 运行，不是业务功能或生产部署方案。

```text
程序化测试入口
  -> Runtime
      -> Execution
          -> Agent
              -> 真实 Model Adapter
              -> In-memory Memory
              -> 无副作用 Tool
          -> Events Collector
      -> 结构化 Runtime Result
```

| 需要证明的能力 | 技术证据 |
|---|---|
| 真实模型调用 | Model ID、usage、延迟和结构化响应 |
| Agent 任务执行 | Model Request 摘要和 Agent Result |
| Tool Call | Tool 名称、参数、结果和事件顺序 |
| Memory | 同 scope 写入和再次召回 |
| Runtime | run_id、唯一终态和取消传播 |
| Streaming | 实际增量事件的转换与合并 |
| Workflow | 顺序、分支、并行、暂停和恢复 |
| 可替换边界 | Adapter Contract Test |
| 架构边界 | Core 依赖检查 |

具体 `RD-*` 输入和断言由第四章定义；模块执行过程由第五章定义；实施顺序由第六章定义。

### 3.9 延后决定的技术选项

以下技术在第一阶段没有足够需求，不提前冻结：

| 技术选项 | 延后原因 | 重新评估时点 |
|---|---|---|
| Pydantic 精确依赖版本 | 公共类型策略已确认，具体版本需结合 uv 工程依赖统一锁定 | A4 建立工程基座时 |
| 多 Provider 路由 | 一个真实 Provider 足以验证 Model Protocol | Model Adapter 稳定后 |
| 持久化 Memory | In-memory 足以验证第一阶段语义 | Memory Contract 通过后 |
| 远程或分布式 Runtime | 会引入调度、网络和状态一致性问题 | 单进程 Runtime 验收后 |
| 完整 Observability 后端 | Events 已能提供第一阶段证据 | 真实业务需要历史查询时 |
| CLI、TUI、HTTP API | Interface 不应反向决定 Kernel | 第一个 Application 稳定后 |
| Dashboard | 不属于 Kernel 学习主路径 | 进入产品化阶段时 |
| RAG、MCP 和向量数据库 | 属于 Application 或 Integration | 对应业务明确后 |
| 生产部署与多租户 | 不影响第一阶段核心语义 | Kernel 基线稳定后 |

延后不表示这些能力不重要，而是避免未出现真实需求前，让外围技术增加 Kernel 学习和实现复杂度。

---

## 4. 测试与验收

本章定义如何证明一个模块既符合公共协议，又能在真实 Agent 链路中承担预期职责。

核心方法是：

> **一个模块，一份合同，一个真实场景，一次累计回归。**

测试不只是实现完成后的质量检查，也是学习 Agent 框架的实验手段。确定性测试帮助理解模块边界，真实对话帮助观察模块在实际运行中的行为。

### 4.1 测试是学习和实现契约

每个模块在实现前必须先定义：

```text
输入
输出
错误
边界
确定性测试
真实对话场景
结构化证据
累计回归范围
```

两种验证方法承担不同职责。

#### 4.1.1 确定性行为采用 TDD

适用于协议、Schema、状态转换、错误处理和依赖方向：

```text
编写失败测试
  -> 实现最小行为
  -> 测试通过
  -> 重构
  -> 再次运行测试
```

确定性测试必须快速、可重复，不依赖网络和真实 Provider。

#### 4.1.2 真实行为采用场景驱动验收

适用于模型生成、Tool Call、Memory 参与、Streaming 和累计运行链路：

```text
定义真实用户输入
  -> 定义模块必须承担的职责
  -> 定义结构化结果或事件
  -> 实现模块
  -> 运行真实 Provider
  -> 保存证据
  -> 回归此前全部场景
```

真实模型响应不采用自然语言全文匹配，而是验证结构化字段、数字事实、Tool 参数、Memory 来源、事件顺序和终态。

### 4.2 双轨验证模型

第一阶段采用两条并行验证轨道。

```text
轨道 A：确定性验证
  Unit
    -> Contract
      -> Architecture

轨道 B：真实链路验证
  Real Model Smoke
    -> Kernel Integration
      -> Progressive Real Dialogue
        -> Application E2E（后续）
```

两条轨道分别证明：

| 验证轨道 | 证明内容 |
|---|---|
| 确定性验证 | 协议、边界、状态转换、错误和依赖方向正确 |
| 真实链路验证 | 真实用户输入能够经过累计 Kernel 链路并产生正确结果 |
| 两条轨道共同通过 | 模块可以标记为完成 |

Unit、Contract 或 Architecture Tests 通过，不能单独证明模块完成；真实对话通过，也不能替代确定性失败路径和架构边界测试。

### 4.3 测试替身使用边界

测试替身只用于构造确定性条件，不能替代主要真实验收。

| 测试场景 | 是否允许测试替身 | 规则 |
|---|---|---|
| Schema 和纯数据转换 | 允许 | 使用固定输入验证确定性输出 |
| Tool 权限、超时和临时错误 | 允许 | 使用受控 Tool 制造明确失败 |
| Memory 存储错误 | 允许 | 使用受控 Adapter 验证错误映射 |
| Runtime 状态转换 | 允许 | 使用确定性执行对象验证生命周期 |
| Provider 错误映射 | 允许补充 | 只补充超时、限流和格式错误覆盖 |
| Agent 完成验收 | 不允许模拟 Model | 必须调用真实 Provider |
| Tool Call 完成验收 | 不允许固定 Tool Call | Tool Call 必须来自真实 Model |
| Memory 完成验收 | 不允许预填召回结果 | MemoryItem 必须来自真实前序运行 |
| Streaming 完成验收 | 不允许固定模型输出 | 必须转换真实 Provider 返回的增量 |
| Workflow 分支验收 | 不允许预填分支结果 | 原始对话必须经过真实 Agent 或 Model |
| 最终回答验收 | 不允许固定答案替身 | 必须经过当前累计真实链路 |

受控测试 Adapter 产生的结果不能被记录为主要真实对话完成证据。

### 4.4 确定性测试

#### 4.4.1 Core Unit Tests

目标：验证单个模块中不依赖外部系统的确定性逻辑。

| 模块 | 测试重点 | 典型用例 |
|---|---|---|
| Agent | 请求组装、结果解析、循环终止 | 缺少输入、非法响应、达到运行上限 |
| Workflow | 状态推进、顺序、分支和恢复 | 分支选择、重复恢复、错误终止 |
| Tool | Schema 和确定性校验 | 缺少字段、非法类型、输出格式错误 |
| Memory | scope 和序列化 | 同 scope 可读、跨 scope 隔离 |
| Model | Request / Response 数据结构 | Tool Call 解析、usage 归一化 |
| Runtime | 生命周期和唯一终态 | completed、failed、cancelled、paused |

Core Unit Tests 不依赖具体 Provider SDK、数据库、业务 Application 或外部 Interface。

#### 4.4.2 Adapter Contract Tests

目标：证明不同具体实现遵守同一份 Kernel Protocol。

| Adapter | 必须证明 |
|---|---|
| Model Adapter | 请求转换、结构化输出、Tool Call、usage、Streaming 和错误语义稳定 |
| Memory Adapter | read、write、search、scope 隔离和序列化稳定 |
| Tool Adapter | 输入校验、输出 Schema、超时、取消和幂等语义稳定 |
| Runtime Adapter | 生命周期、事件顺序、暂停恢复、取消和唯一终态稳定 |

Contract Test 只验证公开行为，不依赖实现内部结构。

具体 Adapter 除共享 Contract 外，还需要对应 Integration Test。真实 Model Adapter 的主要完成证据必须来自真实 Provider。

#### 4.4.3 Architecture Tests

自动检查：

- `agent_kernel/` 不导入 `applications/` 或 `interfaces/`。
- Core 不导入具体 Provider SDK、数据库驱动或 Workflow 框架。
- Adapter 只能实现 Kernel Protocol，不能把实现类型泄漏到 Core。
- Application 只能依赖 Kernel 公开协议。
- Interface 不能绕过 Application 拼装业务 Kernel。
- Integration Fixture 不得被 Core 反向导入。
- 旧项目协议、别名和入口不能进入新 Kernel。
- 六个核心原语之外不能出现未经确认的平行 Core。

Architecture Tests 优先采用 AST 或导入图检查，不使用简单业务关键词全文禁词替代依赖验证。

### 4.5 Kernel 累计集成测试

Kernel Integration 验证多个已实现模块之间的确定性数据流和失败传播。

| 累计链路 | 验证重点 |
|---|---|
| Model Adapter | 统一请求、响应、usage 和错误映射 |
| Model + Agent | Agent 组装请求并返回结构化 AgentResult |
| Agent + Tool | Tool Call、Tool Result 回传和循环终止 |
| Agent + Memory | 同 scope 写入、读取和来源追踪 |
| Runtime + Agent | run_id、Events、Result 和唯一终态 |
| Runtime + Execution | Streaming、Cancellation、Hooks、Guardrails 和 Retry |
| Runtime + Workflow | 顺序、分支、并行、暂停、恢复和幂等 |

Integration Test 可以使用受控输入验证失败传播，但每个累计链路还必须通过对应真实对话场景。

第一阶段没有业务 Application 和正式外部 Interface，因此不把 Kernel Integration 称为产品 E2E。Application、CLI、HTTP 和 Dashboard 的 E2E 在后续阶段单独建立。

### 4.6 渐进式真实对话验收

#### 4.6.1 场景设计规则

每个 `RD-*` 场景必须定义：

```text
test_id
首次引入模块
原始用户输入
模块必须承担的职责
预期结构化断言
预期事件或状态
累计回归范围
阻塞条件
```

统一规则：

- 原始文本必须经过真实 Model 或 Agent 转换为模块输入。
- Fixture 不得预填 Tool 参数、Memory 内容、Workflow 分支、步骤结果或最终答案。
- 数字、枚举、Tool 名称、参数、scope、run_id、事件和终态使用精确断言。
- 自然语言只检查必要语义锚点，不固定完整措辞。
- 每个场景使用独立 run_id、scope 和 Adapter 状态。
- 明确的多轮场景只能在场景内部共享状态。
- Provider 能力不满足时标记 `BLOCKED`，不能等待模型偶然产生预期行为。

#### 4.6.2 真实对话场景矩阵

| ID | 首次引入 | 固定真实输入 | 核心证据 |
|---|---|---|---|
| RD-001 | Model | `请计算 18 + 24，并按指定 JSON Schema 返回 result 整数。` | `result == 42`、model_id、usage、finish_reason、latency |
| RD-002 | Agent | `请完成任务：计算 9 + 6，并返回结构化结果。` | ModelRequest 摘要、`AgentResult.output.result == 15`、stop_reason |
| RD-003 | Tool | `请使用加法工具计算 37 + 58，并告诉我最终结果。` | 真实 Tool Call、参数、ToolResult `95`、事件顺序、最终结果 |
| RD-004 | Memory | 第一轮：`请记住我的项目代号是青岚。`；第二轮：`我的项目代号是什么？` | MemoryItem 来源、同 scope 召回、跨 scope 隔离 |
| RD-005 | Runtime | `请使用加法工具计算 37 + 58，并告诉我最终结果。` | run_id、started 到 completed、Result 与 Events 一致 |
| RD-006 | Workflow | `判断 12 是否为偶数，并执行对应分支。` | 结构化判断、只执行偶数分支、正确终态 |
| RD-007 | Pause / Resume | 第一轮：`生成一条摘要，执行后续动作前等待我确认。`；恢复：`确认继续。` | paused、resume、已完成副作用不重复 |
| RD-008 | Streaming | `请分三步说明如何验证一个函数的输入、处理和输出。` | 实际 chunk 全部消费一次、顺序正确、合并结果一致 |
| RD-009 | Cancellation | `请详细列出二十条代码审查检查项。` | 下游停止、取消后无新 chunk、不得发 completed |
| RD-010 | Hooks / Guardrails | 允许：`请计算 2 + 3。`；拒绝：`BLOCK_TEST：请继续执行。` | Hook 顺序、允许路径真实调用、拒绝路径不调用 Model/Tool |
| RD-011 | Workflow Parallel | `请分别计算 14 + 5 和 8 + 7，最后汇总两个结果。` | 两个 step_started 早于任一完成、结果正确、失败可传播 |
| RD-012 | Retry / Idempotency | `请调用临时查询工具获取编号 R-12，并返回结果。` | 同一幂等键、完整 retry 事件、只产生一次成功副作用 |

补充断言：

- RD-004 第一轮结果必须生成可追溯 MemoryItem，不能直接把答案写入第二轮上下文。
- RD-007 保存可序列化 WorkflowState，恢复后不能重复已完成步骤。
- RD-008 不要求 Provider 固定产生多个 chunk；多 chunk 边界由 Contract Test 补充。
- RD-009 必须在至少收到一个真实增量后取消，并证明 Provider 任务或流已经结束。
- RD-010 的拒绝路径不能替代同一模块允许路径的真实调用。
- RD-011 必须通过同步屏障或等价证据证明执行重叠，并覆盖失败或取消传播。
- RD-012 可以使用受控 Tool 制造第一次临时失败，但 Model、Tool Call、Retry 和最终回答必须经过真实累计链路。
- RD-003 和 RD-012 要求 Provider 支持可确认的 Tool Choice；能力不满足时保持 `BLOCKED`。

#### 4.6.3 累计回归门禁

模块完成必须同时满足：

1. 当前模块 Unit / Contract Tests 通过。
2. 当前模块新增 `RD-*` 场景通过。
3. 此前全部 `RD-*` 场景回归通过。
4. 对应 Architecture Tests 通过。
5. 证据字段完整。
6. 没有使用未授权的模拟输出或 fallback。

状态规则：

| 状态 | 含义 |
|---|---|
| `PASS` | 确定性测试、当前 RD 和历史 RD 全部通过 |
| `FAIL` | 行为或断言不符合规格 |
| `BLOCKED` | 真实 Provider、凭证或必要能力不可用 |
| `NOT RUN` | 测试未执行，不能视为通过 |

任何历史 RD 回归失败，当前模块和当前阶段都不能完成。

### 4.7 断言与证据规则

#### 4.7.1 断言类型

| 数据类型 | 断言方式 |
|---|---|
| 数字和布尔值 | 精确断言 |
| 枚举和终态 | 精确断言 |
| Tool 名称和参数 | 精确断言 |
| run_id、scope、事件类型 | 精确断言 |
| 事件顺序 | 精确顺序或部分顺序断言 |
| 自然语言输出 | 结构化字段或必要语义锚点 |
| usage 和 latency | 存在性、类型和合理范围，不固定精确值 |
| Provider 元数据 | 记录实际值，不泄漏凭证 |

#### 4.7.2 最小证据

每次真实运行至少保存：

```text
test_id
run_id
model_id
provider
raw_dialogue_input
expected_structured_assertions
actual_output_summary
events
usage
latency
error_type
retry_count
status
```

失败时额外记录：

```text
expected
actual
failure_stage
reproducible_command
```

测试证据不能包含 Provider 密钥、完整敏感 Prompt 或不必要的用户隐私数据。

### 4.8 模块验收映射

#### 4.8.1 Kernel 验收矩阵

| ID | 验收能力 | 可观察结果 |
|---|---|---|
| K-001 | Agent 使用真实 Model 完成任务 | 结构化 AgentResult、model_id 和 usage |
| K-002 | Agent 触发 Tool | Tool 输入、结果和后续 Model 调用顺序正确 |
| K-003 | Tool 错误、超时和取消 | 返回稳定错误，不执行非法动作 |
| K-004 | Workflow 顺序和条件分支 | 步骤、分支和结束原因正确 |
| K-005 | Workflow 暂停和恢复 | 从暂停位置继续，不重复副作用 |
| K-006 | Memory 写入和再次读取 | 同 scope 召回，其他 scope 隔离 |
| K-007 | 真实 Model Adapter 契约 | 请求、结果、usage 和错误语义稳定 |
| K-008 | Runtime 取消和 Streaming | 事件顺序正确，取消传播且只结束一次 |
| K-009 | 架构依赖 | Core 不依赖 Application、Interface 或具体实现 |
| K-010 | 累计真实纵向切片 | 六个 Core 和 Execution 在真实链路中协作 |

#### 4.8.2 模块完成映射

| 模块或能力 | 确定性验收 | 真实对话验收 |
|---|---|---|
| Model | K-007 | RD-001 |
| Agent | K-001 | RD-002 |
| Tool | K-002、K-003 | RD-003 |
| Memory | K-006 | RD-004 |
| Runtime | K-008 | RD-005、RD-008、RD-009 |
| Workflow | K-004、K-005 | RD-006、RD-007、RD-011 |
| Hooks / Guardrails | K-008 | RD-010 |
| Retry / Idempotency | K-003、K-008 | RD-012 |
| 架构边界 | K-009 | 全部 RD 场景运行时持续检查 |
| 完整 Kernel | K-010 | RD-001 至 RD-012 |

每个实现任务必须关联至少一个 `K-*` 和一个对应 `RD-*`；纯 Architecture Test 基座任务只关联 K-009，不声明任何模块实现完成。

### 4.9 测试执行与 CI

本地命令统一通过 `uv`：

```bash
uv run pytest -q
ANANHU_REAL_MODEL_SMOKE=1 uv run pytest -q
```

具体测试路径和 pytest markers 在物理目录与测试组织确认后补充，本章不提前冻结。

CI 分层：

1. 每次提交运行文档检查、静态检查、Unit、Contract 和 Architecture Tests。
2. 每个模块完成时运行当前模块 Integration、当前 RD 和此前全部 RD。
3. 具备凭证的受控环境运行 Real Model Smoke、Integration 和 Real Dialogue。
4. 合并前运行完整确定性测试与累计真实对话套件。
5. 定期记录真实模型成本、延迟和 Golden Input 回归。

CI 没有真实 Provider 凭证时：

```text
状态 = NOT RUN
```

不得标记为通过，也不得使用模拟模型替代。

### 4.10 质量与性能基线

#### 4.10.1 Kernel 质量基线

第一阶段先记录事实，不设置缺乏依据的百分比目标：

| 质量维度 | 基线证据 |
|---|---|
| 协议稳定性 | 对应 Contract Tests 是否通过 |
| 架构稳定性 | K-009 是否通过 |
| 真实模型能力 | RD-001、RD-002 是否通过 |
| Tool Call 能力 | RD-003 是否通过 |
| Memory 正确性 | RD-004 是否通过 |
| 生命周期可靠性 | RD-005、RD-007、RD-009 是否通过 |
| Streaming 正确性 | RD-008 是否通过 |
| 并行与重试 | RD-011、RD-012 是否通过 |
| 回归稳定性 | 历史 RD 是否全部通过 |
| 证据完整性 | 最小证据字段是否齐全 |

业务答案质量、RAG 指标和用户体验指标必须等 Application 建立后再定义。

#### 4.10.2 性能基线

性能测试不是第一阶段模块完成门禁，但保留测量入口：

| 测试类型 | 验证点 | 优先级 |
|---|---|---|
| Model 延迟 | Provider P50 / P95 | 中 |
| Runtime 开销 | 排除 Model 后的运行耗时 | 中 |
| Memory 性能 | read、write、search 延迟 | 低 |
| 并发取消 | 多 Run 取消传播 | 低 |
| 长运行内存 | Events 和 Context 是否持续增长 | 低 |

性能数据只能用于发现瓶颈，不能替代正确性与真实链路验收。

---

## 5. 系统架构与模块设计

本章先用整体架构图建立系统全貌，再分别说明核心运行结构、模块职责和数据流。读者应当能够只阅读本章回答：

- 外部请求从哪里进入 Kernel。
- Runtime 如何治理 Agent 或 Workflow。
- Agent 如何使用 Model、Tool 和 Memory。
- Workflow 如何调度步骤并暂停恢复。
- Adapter 在哪里隔离第三方实现。
- Events、Results 和 Errors 从哪里产生并如何被观察。

本章冻结逻辑架构和语义级公共契约，不提前冻结 Python 类型工具、文件名或物理目录。

### 5.1 整体架构图

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                            External Callers（外部调用者）                                  │
│                                                                                          │
│        Programmatic Tests        Future CLI / HTTP        Future Business Interface      │
└──────────────────────────────────────────┬───────────────────────────────────────────────┘
                                           │ structured input / events / result
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                 Interface & Composition（接口与组合层，不属于 Kernel Core）               │
│                                                                                          │
│  ┌──────────────────────────────┐     ┌───────────────────────────────────────────────┐  │
│  │ Interface                   │     │ Application / Test Composition Root           │  │
│  │ 输入转换 | 事件转发          │────►│ 创建 Definition | 选择 Adapter | 注入配置      │  │
│  │ 结果序列化 | 错误映射        │     │ 组装 Runtime、Agent、Workflow、Tool、Memory    │  │
│  └──────────────────────────────┘     └──────────────────────┬────────────────────────┘  │
└─────────────────────────────────────────────────────────────┼────────────────────────────┘
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              Agent Kernel（核心运行层）                                    │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Runtime                                                                            │  │
│  │ Run 创建 | run_id | 生命周期 | pause/resume | cancel | 唯一终态                    │  │
│  │                                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ Execution Governance                                                        │  │  │
│  │  │ RunContext | Hooks | Guardrails | Retry | Cancellation | Streaming           │  │  │
│  │  └───────────────────────────────────┬──────────────────────────────────────────┘  │  │
│  │                                      │ execute target                              │  │
│  │                  ┌───────────────────┴───────────────────┐                         │  │
│  │                  ▼                                       ▼                         │  │
│  │  ┌──────────────────────────────────┐   ┌──────────────────────────────────────┐  │  │
│  │  │ Agent Engine                    │   │ Workflow Engine                      │  │  │
│  │  │                                │   │                                      │  │  │
│  │  │ Memory Read                    │   │ WorkflowState                        │  │  │
│  │  │      ↓                         │   │      ↓                               │  │  │
│  │  │ Model Request Builder          │   │ Step Scheduler                       │  │  │
│  │  │      ↓                         │   │  ├─ Agent Step                       │  │  │
│  │  │ Model ◄──── Tool Result        │   │  ├─ Tool Step                        │  │  │
│  │  │   │              ▲             │   │  ├─ Function Step                    │  │  │
│  │  │   └─ Tool Call ─►Tool          │   │  └─ Branch / Parallel / Pause        │  │  │
│  │  │      ↓                         │   │      ↓                               │  │  │
│  │  │ Memory Write                   │   │ WorkflowResult / paused state        │  │  │
│  │  └──────────────────────────────────┘   └──────────────────────────────────────┘  │  │
│  └─────────────────────────────────────┬────────────────────────────────────────────┘  │
│                                        │                                                │
│          ┌─────────────────────────────┴─────────────────────────────┐                  │
│          ▼                                                           ▼                  │
│  ┌───────────────────────────────────────────────┐  ┌────────────────────────────────┐  │
│  │ Replaceable Capability Contracts             │  │ Structured Evidence            │  │
│  │ Runtime | Model | Tool | Memory Contracts    │  │ Events | Results | Errors      │  │
│  └───────────────────────┬───────────────────────┘  └────────────────┬───────────────┘  │
└──────────────────────────┼───────────────────────────────────────────┼──────────────────┘
                           │ capability calls                          │ evidence export
                           ▼                                           ▼
┌─────────────────────────────────────────────┐       ┌──────────────────────────────────────┐
│ Adapter Layer（实现替换层）                  │       │ Observability / Evidence             │
│ Model Provider | Tool Backend               │       │ Events Collector | Trace Export      │
│ Memory Store | Runtime Adapter              │       │ Test Evidence | Metrics | Logs        │
└──────────────────────┬──────────────────────┘       └──────────────────────────────────────┘
                       │ provider / storage / backend calls
                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                           External Systems（外部实现与资源）                               │
│                                                                                          │
│       Model Provider API        Tool Backend / API        Memory Store        Runtime    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

图中每一层回答不同问题：

| 区域 | 回答的问题 |
|---|---|
| External Callers | 谁发起调用 |
| Interface & Composition | 谁转换输入、选择实现并组装 Kernel |
| Runtime | 谁拥有一次 Run 的生命周期 |
| Agent Engine | 一次智能任务如何形成 Model、Tool、Memory 闭环 |
| Workflow Engine | 多步骤任务如何推进、分支、并行和暂停 |
| Replaceable Contracts | 哪些能力通过稳定协议替换具体实现 |
| Adapter Layer | 第三方实现在哪里接入 |
| Structured Evidence | 系统如何返回结果并证明执行过程 |

整体依赖方向保持：

```text
Interface -> Application / Test Composition -> Kernel Contracts
Adapter -> Kernel Contracts
Kernel -X-> Interface / Application / Provider SDK / 具体存储
```

### 5.2 核心运行架构

Runtime 是所有执行入口，但不接管 Agent 推理或 Workflow 流程语义。

```text
RunRequest
  -> Runtime
      -> 创建 RunContext
      -> 输入 Guardrail
      -> before_run Hooks
      -> 执行 Agent 或 Workflow
          -> 调用 Model / Tool / Memory Contract
          -> 产生增量 Events
      -> 输出 Guardrail
      -> after_run Hooks
      -> RuntimeResult
      -> completed / failed / cancelled / paused
```

核心运行结构分为三类职责：

| 职责 | 所有者 | 说明 |
|---|---|---|
| Run 生命周期治理 | Runtime | run_id、开始、取消、暂停、恢复、终态 |
| 智能执行或流程推进 | Agent / Workflow | 分别拥有推理循环和流程状态 |
| 横切执行约束 | Execution 支撑协议 | Context、Hooks、Guardrails、Retry、Cancellation、Streaming |

Runtime 只能通过公共契约调用目标。第三方运行框架可以实现 Runtime Contract，但不能把框架私有状态泄漏给 Agent、Workflow 或 Application。

### 5.3 模块说明

本节按“定义、输入、核心处理、输出、非职责和验收”说明六个 Core 与 Execution 支撑能力。具体 Python 签名在模块实现前单独确认。

#### 5.3.1 Runtime

目标：负责 Agent 或 Workflow 的完整运行生命周期。

| 项目 | 语义 |
|---|---|
| 输入 | `RunRequest`：已装配目标、对应 Input、调用元数据 |
| 核心处理 | 创建 RunContext、执行目标、传播取消、转发 Streaming、管理暂停恢复和唯一终态 |
| 状态 | run_id、生命周期、resume_token、事件引用 |
| 输出 | `RuntimeResult`：目标结果、运行状态、usage、事件引用和错误 |
| 主要错误 | invalid_request、invalid_resume、timeout、cancelled、internal |
| 非职责 | Agent 推理、Workflow 流程位置、Tool 实现、Memory 存储、Provider 调用 |

验收：K-005、K-008、K-010；RD-005、RD-007、RD-009。

#### 5.3.2 Agent

目标：组合 Instructions、Model、Tools 和 Memory 完成一次智能任务。

| 项目 | 语义 |
|---|---|
| 定义 | `AgentDefinition`：agent_id、Instructions、Model、允许的 Tools、Memory 使用配置、执行上限 |
| 输入 | `AgentInput`：本次任务输入、Memory scope 和调用元数据 |
| 核心处理 | 读取 Memory、组装 ModelRequest、处理 Tool Call 循环、生成最终输出、决定 Memory 写入 |
| 输出 | `AgentResult`：output、tool_calls、usage、stop_reason 和错误 |
| 主要错误 | model、tool、memory、policy、limit、cancelled、internal |
| 非职责 | Workflow 调度、Run 生命周期、Provider SDK、Tool 后端、Memory 存储 |

`AgentDefinition != AgentInput`。Model、Tools 和 Instructions 不应在每次调用时重复作为 AgentInput 传入。

验收：K-001、K-002、K-007；RD-002 至 RD-004。

#### 5.3.3 Workflow

目标：用确定性步骤组合 Agent、Tool 和函数能力。

| 项目 | 语义 |
|---|---|
| 定义 | `WorkflowDefinition`：workflow_id、Steps、依赖关系、分支和暂停点 |
| 输入 | `WorkflowInput`：本次流程初始数据和调用元数据 |
| 状态 | `WorkflowState`：流程位置、已完成步骤、Step Results、分支值和暂停原因 |
| 核心处理 | 调度可执行 Step、保存结果、选择分支、并行无依赖步骤、暂停或结束 |
| 输出 | `WorkflowResult`：output、step_results、state、stop_reason 和错误 |
| 主要错误 | step、branch、state、pause、cancelled、internal |
| 非职责 | 模型生成、Tool 实现、Memory 存储、恢复令牌校验、业务数据库 |

`WorkflowDefinition != WorkflowInput`。并行只是无依赖 Step 的执行策略，不新增核心原语。

验收：K-004、K-005；RD-006、RD-007、RD-011。

#### 5.3.4 Model

目标：提供与 Provider 无关的模型生成能力。

```text
ModelRequest
  -> instructions
  -> input
  -> context
  -> memory_items
  -> tool_schemas
  -> output_schema
  -> runtime_metadata

ModelResponse
  -> text / structured_output
  -> tool_calls
  -> usage
  -> finish_reason
  -> provider_metadata
```

| 项目 | 语义 |
|---|---|
| 调用 | generate；Provider 支持时可以 stream |
| 主要错误 | provider、timeout、rate_limit、format、cancelled |
| 非职责 | Prompt 所有权、Memory、Tool 执行、Workflow 路由、业务规则 |

Agent 负责组装 ModelRequest。Provider SDK 类型只能存在于 Adapter 内部，Provider 特有信息只能进入受控的 `provider_metadata`。

验收：K-001、K-007、K-010；RD-001、RD-008。

#### 5.3.5 Tool

目标：把模型或 Workflow 的结构化意图转换为可治理外部动作。

```text
AgentDefinition 持有可执行 Tool
  -> Agent 提取 ToolDefinition / Tool Schema
  -> ModelRequest 只携带 Tool Schema
  -> ModelResponse 返回 ToolCall
  -> Agent 检查 allowed Tools 并按名称解析 Tool
  -> Input Schema Validation
  -> Runtime / Execution 执行 Guardrail、Permission、Cancellation 和 Idempotency 治理
  -> Tool 调用 Backend
  -> ToolResult
  -> Agent 将 ToolResult 加入下一次 ModelRequest
  -> Model 继续生成最终回答或新的 ToolCall
```

| 项目 | 语义 |
|---|---|
| 可执行 Tool | Kernel 内存中的可调用对象，包含公开 Definition，并实现统一执行契约 |
| Tool Definition / Schema | 名称、说明、输入输出 Schema、权限、超时、取消和幂等声明；这是 Model 能看到的部分 |
| Tool Call | Model 返回的结构化调用意图，至少包含 call_id、工具名称和参数 |
| 输入 | `ToolInput`：已经结构化但仍需校验的调用参数 |
| 输出 | `ToolResult`：结构化 output、执行元数据和错误 |
| 主要错误 | validation、permission、timeout、execution、cancelled |
| 非职责 | 自然语言推理、Prompt、Workflow 路由、重试策略、共享状态 |

Function Calling 的边界固定为：

```text
Tool              != ToolDefinition
ToolDefinition    != ToolCall
ToolCall          != ToolResult
Model 看见 Schema != Model 获得 Python callable
```

统一规则：

- `AgentDefinition` 保存允许使用的可执行 Tool 对象，形成当前 Agent 的 Tool 白名单。
- Model Adapter 只能把 Tool 的名称、说明和参数 Schema 转换到 Provider 请求，不能把 Python 对象、函数或 Backend 暴露给 Provider。
- Model 只负责选择工具并生成结构化参数，不直接执行工具。
- Agent 负责 Tool Call 循环、允许工具检查、按名称解析 Tool，以及把 ToolResult 加入下一次 ModelRequest。
- Tool 负责输入输出契约和一次 Backend 调用，不自行决定是否再次调用 Model。
- Runtime / Execution 负责运行上下文、Guardrail、Permission、Cancellation、Retry 和幂等治理；Retry 仍受 Tool 幂等声明约束。
- Provider 返回的 Tool Call 必须先转换为 Kernel 的统一 `ToolCall`，Provider SDK 类型不能进入 Agent 或 Tool。
- Tool 执行结果必须转换为统一 `ToolResult`，再由 Agent 回传给 Model。

是否重试由 Runtime / Execution 根据错误和幂等声明决定。

验收：K-002、K-003、K-005；RD-003、RD-012。

#### 5.3.6 Memory

目标：按 scope 保存和读取 Agent 可跨运行使用的上下文。

```text
read(scope, query)
write(scope, MemoryItems)
search(scope, query, limit)
```

| 项目 | 语义 |
|---|---|
| 数据 | `MemoryItem`：内容、来源引用、创建时间和可选元数据 |
| 核心处理 | scope 隔离、存储、读取、搜索和序列化 |
| 主要错误 | scope、storage、serialization、cancelled |
| 非职责 | 判断什么值得记忆、WorkflowState、Trace、UI 历史、业务数据库 |

Agent 决定读取和写入时机，并创建带来源的 MemoryItem；Memory 只执行存储语义。

验收：K-006、K-010；RD-004。

#### 5.3.7 Execution 支撑能力

Execution 不是第七个核心原语，而是一组由 Runtime 协调、被执行组件共同遵守的支撑协议。

| 能力 | 作用 | 不能做什么 |
|---|---|---|
| RunContext | 传递 run_id、deadline、metadata 和 cancellation | 不替代 Memory、WorkflowState 或业务状态 |
| Hooks | 观察或扩展生命周期 | 不接管 Agent、Workflow 或 Runtime |
| Guardrails | 在输入、Model 输出和 Tool 调用前后执行约束 | 拒绝后不能继续下游调用 |
| Retry | 对可安全重试的临时失败执行有上限重试 | 不重试权限、Schema、取消或非幂等副作用 |
| Cancellation | 从 Runtime 向下游传播停止信号 | 取消后不能继续产生完成事件 |
| Streaming | 转发真实增量和运行事件 | 不修改最终 Result 或 WorkflowState |

### 5.4 核心数据流

#### 5.4.1 Agent 执行流

```text
AgentInput
  -> Runtime 创建 RunContext
  -> Agent 读取同 scope Memory
  -> Agent 组合 Instructions、Input、MemoryItems 和 Tool Schemas
  -> Model.generate / stream
  -> 无 Tool Call：构建 AgentResult
  -> 有 Tool Call：进入 Tool Call 循环
  -> Agent 根据 Memory 策略创建 MemoryItem
  -> Memory.write
  -> RuntimeResult + terminal Event
```

Agent 的推理循环只属于当前 Run，不使用跨 Run 的共享可变状态。

#### 5.4.2 Tool Call 循环

```text
Application 创建包含可执行 Tools 的 AgentDefinition
  -> Agent 从 Tools 提取 Provider Neutral Tool Schemas
  -> Model Adapter 转换 Tool Schemas 并调用 Provider
  -> Provider Tool Call 转换为 Kernel ToolCall
  -> Agent 检查 Tool 是否在 allowed Tools
  -> Agent 按 ToolCall.name 解析可执行 Tool
  -> ToolInput Schema Validation
  -> Guardrail / Permission / Cancellation / Idempotency
  -> Tool Adapter
  -> External Backend
  -> Kernel ToolResult
  -> Agent 把 ToolResult 加入下一次 ModelRequest
  -> Model 继续生成
  -> 最终回答、新的 ToolCall 或达到执行上限
```

每次 Tool Call 必须产生名称、参数摘要、开始、结果或错误事件。Tool 不自行决定是否再次调用 Model。

#### 5.4.3 Memory 读写流

```text
Application 配置 Agent Memory Policy
  -> Agent 根据 AgentInput.scope 发起 read / search
  -> Memory Adapter 保证 scope 隔离
  -> MemoryItems 回到 Agent
  -> Agent 将相关 MemoryItems 放入 ModelRequest
  -> Agent 从本次执行结果创建新的 MemoryItem
  -> Memory.write
  -> Event 记录 run_id、scope 和来源引用
```

Memory 所有权固定为：

```text
Agent   -> 何时读取、写什么、MemoryItem 来源
Memory  -> 如何存储、搜索和隔离
Runtime -> run_id、生命周期和事件引用
```

#### 5.4.4 Workflow 执行与恢复流

```text
WorkflowInput
  -> Runtime.run
  -> Workflow 创建 WorkflowState
  -> Step Scheduler 选择可执行步骤
      -> Agent Step
      -> Tool Step
      -> Function Step
      -> Branch / Parallel
  -> 保存 StepResult 和流程位置
  -> complete / fail
  -> 或 paused + WorkflowState

resume_input + resume_token
  -> Runtime 校验 token、Run 和终态
  -> Runtime 取回对应 WorkflowState
  -> Workflow 从明确位置继续
  -> 已完成副作用步骤不得重复
```

Workflow 拥有流程位置和 WorkflowState；Runtime 拥有恢复请求验证和一次性 `resume_token`。`resume_token` 不进入 WorkflowState。

### 5.5 Adapter 与配置驱动

Adapter 层把稳定能力协议连接到具体实现：

| Contract | 第一阶段参考实现 | 后续替换示例 | Core 保持稳定 |
|---|---|---|---|
| Model | 一个真实 Provider Adapter | 其他云模型或本地模型 | ModelRequest、ModelResponse、Tool Call、usage、错误 |
| Tool | 无副作用结构化 Tool | HTTP API、MCP、数据库或本地函数 | ToolInput、ToolResult、权限、幂等、错误 |
| Memory | In-memory Adapter | 文件、数据库或语义检索存储 | read、write、search、scope |
| Runtime | 单进程 Local Runtime | 第三方框架或远程 Runtime | 生命周期、Events、取消、暂停恢复、Result |

配置和依赖注入只在 Composition Root 执行：

```text
环境变量 / 配置文件
  -> 校验 Adapter Config
  -> 创建具体 Adapter
  -> 创建 AgentDefinition / WorkflowDefinition
  -> 注入 Runtime
  -> 执行真实 RD 场景
```

规则：

- Core 不读取环境变量、凭证或 Provider 配置。
- 模型标识属于运行配置，不属于 Kernel 架构常量。
- Provider 能力、凭证和配置必须在运行前校验。
- 不允许自动切换到模拟 Model、固定输出或未确认 Provider。
- 替换 Adapter 后必须重跑对应 Contract Test 和累计 RD 场景。

第一条参考组合：

```text
Programmatic Test Entry
  -> Test Composition Root
      -> Local Runtime
          -> Agent
              -> Real Model Adapter
              -> In-memory Memory Adapter
              -> No-side-effect Tool
          -> Events Collector
      -> AgentResult + RuntimeResult
```

### 5.6 扩展性设计要点

新增能力必须找到明确扩展位置：

| 新增内容 | 扩展位置 | 禁止做法 |
|---|---|---|
| Model Provider | 新增 Model Adapter | 修改 Agent 适配某个 SDK |
| Memory Store | 新增 Memory Adapter | 把数据库类型传入 Agent |
| Tool Backend | 实现 Tool Contract | 让 Tool 接管推理或 Workflow |
| Runtime Engine | 实现 Runtime Contract | 泄漏第三方框架状态 |
| 业务 Agent / Workflow | Application 组合 | 把业务 Prompt 和规则写入 Kernel |
| Interface | Application 外层 | 绕过 Application 重新实现 Kernel |
| Observability | Events / Hooks Adapter | 修改 Core Result 语义 |

扩展前必须更新完整规格、对应版本文档、Contract Test 和真实对话场景。

### 5.7 状态与数据所有权

| 数据或状态 | 主要所有者 | 创建或修改规则 |
|---|---|---|
| Agent Instructions、Model、Tools、Memory 使用策略 | `AgentDefinition` | Application / Test Composition Root 创建，运行中只读 |
| 本次 Agent 任务和调用参数 | `AgentInput` | 调用方为每次运行创建 |
| Workflow Steps 和流程拓扑 | `WorkflowDefinition` | Application 创建，运行中只读 |
| 本次 Workflow 初始数据 | `WorkflowInput` | 调用方为每次运行创建 |
| Agent 推理循环和 Tool Call 历史 | `Agent` | 只在当前 Run 内推进 |
| 流程位置和 Step Results | `WorkflowState` | 只由 Workflow 推进并序列化 |
| run_id、生命周期和终态 | `Runtime` | Runtime 创建并保证唯一终态 |
| resume_token | `Runtime` | Runtime 创建、校验、消费和失效 |
| MemoryItem 内容和来源 | `Agent` | Agent 根据 Memory Policy 创建 |
| Memory scope 隔离和持久化 | `Memory` | Memory Adapter 执行 |
| Provider 请求响应转换 | `Model Adapter` | 转换为统一 Model 协议 |
| 业务 Prompt、规则和业务状态 | `Application` | 不进入 Kernel 通用状态 |

#### 5.7.1 Definition 类型规则

`AgentDefinition`、`WorkflowDefinition` 和 `ToolDefinition` 使用只读 dataclass 表达：

```python
@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
    eq=False,
)
class ComponentDefinition:
    ...
```

统一规则：

- Definition 是只读装配对象，不是 Input、State、Context 或 Result。
- Definition 必须提供稳定的 `definition_id` 和 `revision`。
- Definition 可以引用 Model、Tool 等 Protocol 实例，因此不承诺整体 JSON 序列化。
- `eq=False` 避免对 Model、Tool、函数包装器等运行对象进行结构相等比较；身份一致性由 `definition_id + revision` 显式判断。
- Definition 内部集合使用 `tuple`、`frozenset` 或等价不可变值对象，不保存可原地修改的 `list`、`set` 或 `dict`。
- 修改 Definition 必须创建新对象并更新 revision，不能在运行中原地修改。
- `__post_init__` 只校验 definition_id、revision、执行上限等本地装配不变量，不执行 Provider 网络或凭证检查。
- Provider 凭证、SDK 配置、run_id、Tool Call 历史和 WorkflowState 不得进入 Definition。
- 暂停恢复数据只保存可序列化的 `DefinitionRef(definition_id, revision)`，由 Application / Composition Root 重新提供对应 Definition。
- 恢复时 DefinitionRef 与实际 Definition 不一致，必须返回明确恢复错误，不能自动使用新版本继续旧状态。

Definition 的具体业务字段仍由对应 B-G 任务确认，本节只冻结公共 Python 类型和生命周期规则。

#### 5.7.2 Input 类型规则

`AgentInput`、`WorkflowInput`、`ToolInput`、`ModelRequest` 和 `RunRequest` 使用严格、不可变的 Schema Model 表达。

公共 Schema 基类只统一 Pydantic 配置，不定义万能公共字段：

```python
class KernelSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )
```

统一规则：

- 每个 Input 只保存对应模块本次调用需要的数据，不能重复携带 Definition 中已有的 Model、Tools、Instructions 或 Workflow 拓扑。
- Input 创建后不可修改；新的调用数据必须创建新的 Input 和新的 Run。
- `frozen=True` 只提供浅层冻结；嵌套 Schema 也必须冻结，集合优先使用 tuple，开放 JSON 必须防御性复制或规范化，不能保留调用方可变引用。
- `extra="forbid"` 拒绝拼错字段、未声明参数和外围私有字段静默进入 Kernel。
- `strict=True` 禁止把错误类型自动转换为目标类型；Model 生成的非法 Tool 参数必须形成明确 validation 错误。
- Input 必须能够稳定序列化为 JSON，不包含 Protocol、callable、可执行 Tool、Provider SDK 类型或凭证。
- 公共字段必须使用明确类型，不使用 `Any` 绕过契约。
- KernelSchema 不提供 run_id、scope、metadata、provider 等万能字段；共享字段只在确有相同语义的具体 Input 中显式声明。
- run_id、deadline 和 cancellation 属于 RunContext；运行中产生的数据属于 State、Event 或 Result，不能回填 Input。
- 不创建 UniversalInput，也不通过继承让无关模块获得彼此字段。

Input 的具体字段和嵌套 Schema 由对应 B-G 任务确认，本节只冻结严格校验、不可变和模块隔离规则。

#### 5.7.3 Result 类型规则

`ModelResponse`、`AgentResult`、`ToolResult`、`WorkflowResult` 和 `RuntimeResult` 使用模块独立的严格 Schema Model 表达，不创建万能 `KernelResult`。

统一规则：

- Result 表达一次模块调用的最终结构化结果，不承担 Input、State、Event 或完整 Trace 的职责。
- Result 继承 KernelSchema，保持 `frozen=True`、`extra="forbid"` 和 `strict=True`。
- 能够以成功、失败、取消或暂停结束的 Result 必须使用模块专属 `str Enum` 表达明确状态，不使用 `success: bool` 压缩不同终态。
- 各模块只声明自己真实支持的状态；例如 `paused` 只属于支持暂停语义的 Workflow / Runtime 结果。
- Result 必须使用 Pydantic model validator 校验 status、output、error 和 state 的合法组合。
- 成功结果不能同时携带 ErrorInfo；失败结果必须携带 ErrorInfo；暂停结果必须携带可恢复 State 或其稳定引用。
- Result 输出使用明确的 Provider Neutral 类型，不使用 `Any`，不保存 Provider SDK 响应对象或凭证。
- Result 可以保存归一化 usage、stop_reason、必要调用摘要和事件引用，但不复制全部 Events、日志、完整 Prompt 或其他模块内部状态。
- 内部 Exception 在明确模块边界转换为可序列化 ErrorInfo；具体捕获层级和映射由 Error 类型规则及 B-G 任务确认。
- Streaming 增量和 Events 先独立产生，流结束后只创建一次最终 Result；最终内容必须与已消费增量一致。
- `RuntimeResult != AgentResult != WorkflowResult != ToolResult`，上层结果只能引用或组合下层公开结果，不能继承为同一万能对象。

具体状态枚举、必填输出和 ErrorInfo 组合规则仍由对应 B-G 任务确认，本节只冻结结构化终态和不变量策略。

#### 5.7.4 Event 类型规则

Event 使用“公共信封 + 具体事件 Schema + 判别联合”表达。

公共信封至少提供：

```text
event_id
run_id
sequence
occurred_at
source
```

具体事件使用稳定 `type` 字段和明确负载字段，并通过 Pydantic discriminated union 组合：

```python
KernelEvent = Annotated[
    RunStartedEvent
    | ToolCallStartedEvent
    | ToolCallCompletedEvent
    | RunCompletedEvent
    | RunFailedEvent,
    Field(discriminator="type"),
]
```

统一规则：

- Event 表达已经发生的结构化事实，不是 Command、State、Result 或普通日志。
- Event 继承 KernelSchema，创建后不可修改，只能追加。
- 只共享一层 EventEnvelope，不建立多层事件继承体系。
- 每一种事件使用独立 Schema 和稳定的 Literal type，不使用 `payload: dict[str, Any]` 万能负载。
- Runtime 保证同一 run_id 内 sequence 单调递增；事件顺序以 sequence 为准，不依赖时间戳排序。
- occurred_at 统一使用 UTC，只用于观察、耗时和证据记录。
- 并行事件通过 sequence 以及 step_id、call_id 等关联字段表达观察顺序。
- 每个 Run 只能产生一个 Terminal Event；cancelled 或 failed 后不得再产生 completed。
- WorkflowState 是暂停恢复的事实源，Events 不作为第一阶段的状态回放存储。
- Result 可以保存事件引用或摘要，但不能复制完整 Events。
- Event 不保存 Provider 密钥、完整敏感 Prompt、Backend 凭证、Provider 原始响应或不必要的用户隐私。
- Tool 参数和输出默认进入脱敏的 arguments_summary / output_summary；完整测试证据由受控工件单独保存。
- Streaming 增量是否作为具体事件类型由 F3 确认；若进入 Event，仍必须遵守同一信封、顺序和唯一终态规则。

具体事件清单和字段由对应 D-G 任务确认，本节只冻结事件类型表达、顺序和边界。

#### 5.7.5 Error 类型规则

错误采用 `KernelError + ErrorInfo` 双层模型：

```text
KernelError -> Python 运行时中断和向上层传播
ErrorInfo   -> Result、Event 和测试证据中的可序列化错误
```

统一规则：

- KernelError 只建立少量需要不同捕获边界的领域异常，例如 ModelInvocationError、ToolExecutionError、MemoryOperationError、WorkflowExecutionError、RuntimeExecutionError 和 KernelCancellationError。
- 具体错误差异优先使用稳定的分域 ErrorCode 表达，不为每个错误码创建异常子类。
- ErrorCode 使用 `model.timeout`、`tool.validation`、`workflow.revision_mismatch` 等 Provider Neutral 字符串，不直接暴露 Provider 原始错误码。
- Provider SDK Exception 必须在对应 Adapter 边界映射为 KernelError，并使用异常链保留内部 cause。
- ErrorInfo 继承 KernelSchema，至少表达 code、message、source、retryable 和脱敏 details。
- Exception、traceback、Provider SDK 对象、凭证、完整请求响应和未脱敏用户数据不得进入 ErrorInfo。
- 合法运行开始前的无效 Definition 或 Input 构造直接抛出 ValueError / Pydantic ValidationError，不伪装成一次正常 failed Result。
- 合法运行中的 Model、Tool、Memory、Workflow 或 Runtime 操作失败通过 KernelError 传播，并在明确模块边界转换为 failed Result 和 failure Event 中的 ErrorInfo。
- `retryable=True` 只表示错误类型允许重试；真正重试还必须满足幂等或幂等键、Retry Policy、次数、deadline 和未取消条件。
- Permission、Schema、Cancellation 和非幂等副作用失败不得因为 retryable 字段被自动重试。
- ErrorInfo 的 message 和 details 必须适合公开证据；完整内部诊断只进入受控日志或异常链。

具体 ErrorCode 清单、异常捕获层级和 Result 映射由对应 B-G 任务确认，本节只冻结双层错误表达和安全边界。

#### 5.7.6 State 类型规则

State 使用模块独立、严格、不可变且可完整 JSON 往返的 Schema Model 表达。第一阶段最主要的公开 State 是 WorkflowState，不创建万能 `KernelState`。

统一规则：

- State 表达可继续执行组件的当前可恢复快照，不承担 Definition、Input、Memory、RunContext、Event 或 Result 的职责。
- 每次状态转换创建新的 State 实例，禁止原地修改 completed_steps、position、branch values 等字段。
- 状态转换必须重新执行 Schema 和业务不变量校验，不能依赖可能绕过完整校验的复制更新。
- State 只包含标量、str Enum、UTC datetime、冻结嵌套 Schema、稳定集合、受约束 JsonValue、DefinitionRef 和结构化步骤结果或引用。
- State 不包含 Model、Tool、Protocol、callable、asyncio Task / Lock / Event、Cancellation Token、数据库连接、Provider SDK 对象、Exception 或 Runtime 内存引用。
- 每种 State 必须通过 `model_dump_json -> model_validate_json` 往返测试，并保持语义等价。
- DefinitionRef.revision 表达 Definition 拓扑版本；state_schema_version 表达序列化结构版本，两者必须独立校验。
- 第一阶段不自动迁移未知 Definition revision 或 State schema version，必须返回明确的 revision mismatch 或 unsupported schema 错误。
- checkpoint_id 可以进入 State，用于标识保存快照；resume_token 属于 Runtime 的一次性恢复授权，禁止进入 State。
- Workflow 创建、解释和推进 WorkflowState；Runtime 只负责保存、取回、token 校验和恢复驱动，不修改 Workflow 语义字段。
- State Store Adapter 只执行持久化语义，不解释步骤位置或分支。
- Events 是审计证据，不是第一阶段恢复事实源；第一阶段不实现 Event Sourcing。
- resume_token 必须绑定 run_id、checkpoint_id 和 DefinitionRef，成功消费后立即失效，重复恢复不得再次执行已完成副作用。

WorkflowState 的具体字段和恢复协议由 G1、G4 确认，本节只冻结 State 的类型、序列化和所有权规则。

#### 5.7.7 JSON 与 metadata 公共边界

公共协议禁止使用 `Any`、`object` 和无类型 `dict` 绕过结构化契约。

开放 JSON 数据只允许以下递归类型：

```python
JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]
```

统一规则：

- 上述别名描述 JSON wire shape，不表示 Kernel 可以长期保留外部传入的可变 list / dict 引用。
- Schema 构造边界必须对开放 JSON 做防御性复制和规范化；State、Event 等不可变对象不能向调用方暴露可原地修改其内部语义的引用。
- 内存中的深度不可变表示和 JSON wire shape 必须可以稳定互转；具体 Frozen JSON 容器实现由 A4 确认。
- 已知结构必须定义明确 Schema；JsonValue 只用于真正开放的 Model 输出、Tool 通用包装、受控 metadata 和脱敏 Provider 扩展信息。
- datetime、Enum、UUID、Decimal 和 bytes 不能作为任意 Python 对象进入 JsonValue，必须按字段契约显式转换。
- float 必须是有限值，禁止 NaN、Infinity 和 -Infinity 进入公共 JSON。
- metadata 只能在确有扩展需求的具体 Schema 中显式声明，不能进入 KernelSchema 基类。
- 每个 metadata 字段必须明确写入者、读取者、是否参与核心逻辑、是否持久化、敏感数据规则和大小限制。
- application metadata、runtime_metadata 和 provider_metadata 必须分域，不能互相覆盖正式字段。
- Kernel 核心逻辑不能依赖 provider_metadata 做分支、状态推进或重试决定。
- Provider Adapter 只能按白名单提取 request_id、model_version 等必要字段，禁止复制原始响应、请求头、凭证或 SDK 对象。
- 需要哈希、幂等键、Checkpoint 完整性或证据比较时，必须使用统一 Canonical JSON，不使用 Python repr 或无规范序列化。
- Canonical JSON 至少固定 UTF-8、key 排序、稳定分隔符、有限浮点、Enum value 和 UTC ISO 8601 datetime。
- 开放 JSON 必须设置最大嵌套深度、key 数、字符串长度和序列化字节数；具体阈值由使用该字段的 B-G 任务确认。
- 超出 JSON 边界必须产生稳定的 schema.json_too_deep、schema.json_too_large 或等价 ErrorCode。

JsonValue 的具体 Python 实现、Canonical JSON 函数和限制值由 A4 及首个使用任务确认，本节只冻结公共数据边界。

必须保持：

```text
AgentDefinition != AgentInput
WorkflowDefinition != WorkflowInput
WorkflowState != Memory
RunContext != WorkflowState
RuntimeResult != AgentResult != WorkflowResult != ToolResult
```

### 5.8 物理目录决策状态

物理目录结构当前为“待确认”，不是实现事实。此前文档中的扁平 Core 布局和 `core` 嵌套布局均已取消。

正式目录必须在首个模块实现前，根据以下事实单独设计和确认：

- 六个 Core 的公开 API 和参考实现。
- Definition、Input、Result 和支撑协议的归属。
- Adapter 与 Core 的导入方向。
- Contract、Integration、Architecture 和 RD 测试组织。
- 对外公开导入路径。

目录确认前不得创建 Kernel 代码目录，也不得从旧项目恢复工程结构。

---

## 6. 项目排期

### 6.1 排期原则

第六章既是学习路线，也是实现进度入口。目录必须直接展示每个任务，正文则说明学习问题、前置依赖、交付和验收。

统一规则：

- 每个任务只引入一个主要机制或一个明确验收出口。
- 先完成最小真实链路，再逐步加入 Tool、Memory、Runtime 和 Workflow。
- 确定性行为使用 Unit、Contract 和 Architecture Tests。
- 模型相关完成证据必须来自真实 Provider 和固定 RD 场景。
- 每个阶段出口都必须运行当前 RD 和此前全部 RD。
- 任务完成必须产生可检查的协议、实现、测试或证据，不能只创建空目录。
- 未确认物理目录和 Python 类型前，排期不反向冻结文件路径、类名或库。
- Application、Interface 和业务 Evals 属于 Kernel 完成后的扩展路线，不进入本章第一阶段排期。

任务状态：

```text
[ ] 未开始
[~] 进行中
[x] 已完成
[!] 阻塞
```

测试状态继续使用第四章定义的 `PASS`、`FAIL`、`BLOCKED` 和 `NOT RUN`。

### 6.2 学习与实现依赖链

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

该顺序用于逐步暴露 Agent 框架机制：

| 阶段 | 首要学习问题 | 阶段结束后的可观察能力 |
|---|---|---|
| A | 如何让设计、目录、类型和测试基座一致 | 项目具备实现准入条件 |
| B | 如何隔离统一模型协议与 Provider | 真实模型返回统一结构化结果 |
| C | Agent 如何把输入变成一次智能任务 | 最小 Agent 可完成真实任务 |
| D | 模型意图如何变成受治理外部动作 | 真实 Tool Call 闭环可运行 |
| E | 上一次运行的信息如何参与下一次运行 | 同 scope 两轮对话可以召回 |
| F | 一次 Run 如何被治理、观察和终止 | 生命周期、事件和执行策略可验证 |
| G | 多步骤任务如何确定性推进 | Workflow 可分支、并行、暂停和恢复 |
| H | 如何证明 Kernel 整体成立 | 全部合同、架构边界和 RD 通过 |

### 6.3 阶段总览

| 阶段 | 名称 | 任务数 | 出口验收 | 状态 |
|---|---|---:|---|---|
| A | 规格与实现准入 | 5 | 目录、类型、工程和证据基座确认 | 进行中 |
| B | Model MVP | 6 | RD-001 | 待开始 |
| C | Agent MVP | 5 | RD-002 + RD-001 回归 | 待开始 |
| D | Tool Call 闭环 | 6 | RD-003 + 历史 RD 回归 | 待开始 |
| E | Memory 跨运行上下文 | 6 | RD-004 + 历史 RD 回归 | 待开始 |
| F | Runtime 与 Execution | 8 | RD-005、RD-008 至 RD-010、RD-012 + 历史 RD | 待开始 |
| G | Workflow 控制语义 | 6 | RD-006、RD-007、RD-011 + 历史 RD | 待开始 |
| H | Kernel 累计验收与发布 | 5 | K-001 至 K-010、RD-001 至 RD-012 | 待开始 |

### 6.4 进度跟踪表

#### 6.4.1 阶段 A：规格与实现准入

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| A1 | 完成开发规格逐章确认 | [x] | 第 1-7 章一致 |
| A2 | 确认公共类型表达策略 | [x] | Python 类型与序列化规则 |
| A3 | 确认物理目录与公开导入路径 | [ ] | 可实施目录设计 |
| A4 | 建立 uv、pytest 与 Architecture Test 基座 | [ ] | 可运行工程 |
| A5 | 建立真实对话证据基座 | [ ] | RD 执行和证据入口 |

#### 6.4.2 阶段 B：Model MVP

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| B1 | 定义 ModelRequest 与 ModelResponse | [ ] | Provider Neutral 数据协议 |
| B2 | 定义 Model Contract 与错误语义 | [ ] | generate / stream 契约 |
| B3 | 实现首个真实 Model Provider Adapter | [ ] | 真实 Provider 可调用 |
| B4 | 实现结构化输出转换 | [ ] | 统一结构化结果 |
| B5 | 实现 Provider Streaming 转换 | [ ] | 有序真实增量 |
| B6 | 完成 RD-001 真实模型验收 | [ ] | Model MVP 完成证据 |

#### 6.4.3 阶段 C：Agent MVP

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| C1 | 定义 AgentDefinition、AgentInput 与 AgentResult | [ ] | Agent 调用边界 |
| C2 | 实现 Instructions 与 ModelRequest 组装 | [ ] | Prompt 所有权落地 |
| C3 | 实现最小 Agent 推理循环 | [ ] | Input -> Model -> Result |
| C4 | 实现运行上限与停止原因 | [ ] | 明确循环终止 |
| C5 | 完成 RD-002 Agent 真实任务验收 | [ ] | Agent MVP 完成证据 |

#### 6.4.4 阶段 D：Tool Call 闭环

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| D1 | 定义 Tool、ToolInput 与 ToolResult | [ ] | Tool 调用边界 |
| D2 | 实现 Tool Schema 校验 | [ ] | 确定性输入输出 |
| D3 | 实现允许工具解析与调用 | [ ] | Tool 选择和执行 |
| D4 | 实现 Tool Result 回传 Model | [ ] | 多轮 Tool Call 循环 |
| D5 | 实现权限、超时与幂等声明 | [ ] | Tool 治理元数据 |
| D6 | 完成 RD-003 Tool Call 验收 | [ ] | Tool MVP 完成证据 |

#### 6.4.5 阶段 E：Memory 跨运行上下文

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| E1 | 定义 Memory Contract 与 MemoryItem | [ ] | Memory 调用边界 |
| E2 | 实现 In-memory Memory Adapter | [ ] | 最小可运行存储 |
| E3 | 实现 scope 隔离 | [ ] | 跨 scope 不可见 |
| E4 | 实现 Agent Memory 读取策略 | [ ] | Memory 参与 ModelRequest |
| E5 | 实现 Agent Memory 写入策略 | [ ] | 可追溯 MemoryItem |
| E6 | 完成 RD-004 两轮对话验收 | [ ] | Memory MVP 完成证据 |

#### 6.4.6 阶段 F：Runtime 与 Execution

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| F1 | 定义 RunRequest、RunContext 与 RuntimeResult | [ ] | Runtime 调用边界 |
| F2 | 实现 Runtime 生命周期与唯一终态 | [ ] | started -> terminal |
| F3 | 实现 Events 与 Streaming | [ ] | 有序增量和事件 |
| F4 | 实现 Cancellation 传播 | [ ] | 下游停止 |
| F5 | 实现 Hooks | [ ] | 生命周期扩展 |
| F6 | 实现 Guardrails | [ ] | 允许和拒绝路径 |
| F7 | 实现 Retry 与幂等治理 | [ ] | 安全重试 |
| F8 | 完成 Runtime / Execution 真实验收 | [ ] | RD-005、RD-008 至 RD-010、RD-012 |

#### 6.4.7 阶段 G：Workflow 控制语义

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| G1 | 定义 WorkflowDefinition、Input、State 与 Result | [ ] | Workflow 调用边界 |
| G2 | 实现顺序步骤执行 | [ ] | 确定性推进 |
| G3 | 实现条件分支 | [ ] | 结构化分支 |
| G4 | 实现暂停与恢复 | [ ] | 可序列化恢复 |
| G5 | 实现无依赖步骤并行 | [ ] | 并发和失败传播 |
| G6 | 完成 Workflow 真实验收 | [ ] | RD-006、RD-007、RD-011 |

#### 6.4.8 阶段 H：Kernel 累计验收与发布

| ID | 任务 | 状态 | 主要出口 |
|---|---|---|---|
| H1 | 六个 Core Contract 累计回归 | [ ] | 协议证据 |
| H2 | Architecture Tests 与依赖扫描 | [ ] | 边界证据 |
| H3 | RD-001 至 RD-012 累计回归 | [ ] | 真实链路证据 |
| H4 | 发布首个完整架构版本 | [ ] | 架构快照与 changelog |
| H5 | 完善 Kernel README 与学习记录 | [ ] | 可复现学习成果 |

### 6.5 总体进度

| 阶段 | 总任务 | 已完成 | 进行中 | 进度 |
|---|---:|---:|---:|---:|
| A | 5 | 2 | 0 | 40% |
| B | 6 | 0 | 0 | 0% |
| C | 5 | 0 | 0 | 0% |
| D | 6 | 0 | 0 | 0% |
| E | 6 | 0 | 0 | 0% |
| F | 8 | 0 | 0 | 0% |
| G | 6 | 0 | 0 | 0% |
| H | 5 | 0 | 0 | 0% |
| **总计** | **47** | **2** | **0** | **4%** |

只有 `[x]` 计入完成进度；`[~]`、`[!]` 和测试状态 `BLOCKED`、`NOT RUN` 均不计入。

### 6.6 详细实施任务

#### 6.6.1 阶段 A：规格与实现准入

目标：在创建 Kernel 代码目录前，完成设计、类型、目录、工程和真实证据入口的全部准入条件。

##### A1：完成开发规格逐章确认

- 学习问题：完整规格如何避免模块设计、测试和排期互相冲突。
- 前置依赖：第 1-7 章已确认。
- 交付：第 1-7 章完整审查结果和当前事实源。
- 验收：章节职责不重叠，版本、索引、链接和门禁一致。
- 证据：[`A1 规格确认与实现准入记录`](docs/superpowers/specs/2026-07-13-agent-kernel-implementation-admission-a1.md)。
- 关联：[`docs/superpowers/specs/README.md`](docs/superpowers/specs/README.md) 中的实现准入门禁 1-6。

##### A2：确认公共类型表达策略

- 学习问题：何时使用 Protocol、ABC、dataclass 或 Schema Model。
- 前置依赖：A1、第五章语义级公共契约。
- 交付：Definition、Input、Result、Event、Error 和 State 的类型策略。
- 验收：Provider 类型不泄漏，跨 Adapter 和暂停恢复数据可序列化。
- 证据：[`A2 公共类型表达策略确认记录`](docs/superpowers/specs/2026-07-13-agent-kernel-public-type-strategy-design.md)。
- 关联：K-009、全部 Contract Tests。

##### A3：确认物理目录与公开导入路径

- 学习问题：逻辑边界如何转换为 Python 包和单向导入关系。
- 前置依赖：A2。
- 交付：完整目录树、公开 API、Adapter 和测试组织。
- 验收：用户确认；不存在平行 Core、循环依赖或旧项目入口。
- 关联：K-009。

##### A4：建立 uv、pytest 与 Architecture Test 基座

- 学习问题：如何用工程工具持续保护架构边界。
- 前置依赖：A3。
- 交付：Python 3.11 工程、uv 依赖入口、pytest 和导入边界检查。
- 验收：空白 Kernel 工程可安装、可导入、可运行确定性测试。
- 关联：K-009；不声明任何 Core 完成。

##### A5：建立真实对话证据基座

- 学习问题：如何保存真实 Provider 运行结果而不依赖自然语言全文。
- 前置依赖：A4、第四章证据规则。
- 交付：RD 场景入口、隔离 run_id/scope、状态和证据格式。
- 验收：可以记录 `PASS`、`FAIL`、`BLOCKED`、`NOT RUN`，且不泄漏凭证。
- 关联：RD-001 至 RD-012 的公共基座。

#### 6.6.2 阶段 B：Model MVP

目标：建立第一个 Provider Neutral 模型协议，并通过真实 Provider 得到结构化结果。

##### B1：定义 ModelRequest 与 ModelResponse

- 学习问题：Agent 和 Provider 之间真正需要交换哪些数据。
- 前置依赖：A2、A4。
- 交付：请求、响应、Tool Call、usage 和 finish_reason 数据语义。
- 验收：可序列化；不包含具体 Provider SDK 类型。
- 关联：K-001、K-007。

##### B2：定义 Model Contract 与错误语义

- 学习问题：如何让不同 Provider 遵守同一调用行为。
- 前置依赖：B1。
- 交付：generate、stream 能力和 provider、timeout、rate_limit、format、cancelled 错误。
- 验收：共享 Contract Test 能约束成功和失败路径。
- 关联：K-001、K-007、K-010。

##### B3：实现首个真实 Model Provider Adapter

- 学习问题：如何在不污染 Core 的前提下转换 Provider 请求响应。
- 前置依赖：B2、Provider 配置确认。
- 交付：一个真实 Provider Adapter 和能力预检。
- 验收：凭证、模型和能力错误明确；不得 fallback 到模拟输出。
- 关联：K-001、K-007。

##### B4：实现结构化输出转换

- 学习问题：如何把不稳定自然语言响应转换为稳定协议。
- 前置依赖：B3。
- 交付：结构化输出请求、解析和格式错误映射。
- 验收：固定 Schema 请求得到可精确断言的结构化结果。
- 关联：RD-001。

##### B5：实现 Provider Streaming 转换

- 学习问题：如何将 Provider 增量统一成 Kernel 增量语义。
- 前置依赖：B3。
- 交付：有序增量、结束原因和合并规则。
- 验收：完整消费后合并结果与最终 ModelResponse 一致。
- 关联：K-007；RD-008 的前置能力。

##### B6：完成 RD-001 真实模型验收

- 学习问题：统一 Model Contract 是否真的承载真实模型能力。
- 前置依赖：B4、A5。
- 交付：固定输入 `18 + 24` 的真实结构化运行证据。
- 验收：`result == 42`，并记录 model_id、provider、usage、finish_reason 和 latency。
- 关联：RD-001；阶段 B 出口。

#### 6.6.3 阶段 C：Agent MVP

目标：实现不含 Tool 和跨运行 Memory 的最小 Agent 推理闭环。

##### C1：定义 AgentDefinition、AgentInput 与 AgentResult

- 学习问题：Agent 长期组合和单次调用如何分离。
- 前置依赖：B6。
- 交付：Definition、Input、Result 和错误边界。
- 验收：Model、Instructions 和执行上限属于 Definition，不进入每次 Input。
- 关联：K-001、K-007。

##### C2：实现 Instructions 与 ModelRequest 组装

- 学习问题：业务 Instructions、用户输入和运行上下文如何进入模型请求。
- 前置依赖：C1、B1。
- 交付：确定性的 ModelRequest Builder。
- 验收：请求内容和来源可检查，Provider 配置不进入 Agent。
- 关联：K-001。

##### C3：实现最小 Agent 推理循环

- 学习问题：Agent 与单次 Model 调用的本质区别是什么。
- 前置依赖：C2、B3。
- 交付：AgentInput -> Model -> AgentResult 的最小循环。
- 验收：成功、Model 错误和取消语义能够映射到 AgentResult。
- 关联：K-001、K-007。

##### C4：实现运行上限与停止原因

- 学习问题：如何防止 Agent 无限执行并解释停止原因。
- 前置依赖：C3。
- 交付：最大模型轮次、stop_reason 和 limit 错误。
- 验收：正常完成、格式失败、取消和达到上限可区分。
- 关联：K-001。

##### C5：完成 RD-002 Agent 真实任务验收

- 学习问题：Agent 是否真正承担了请求组装和结果生成职责。
- 前置依赖：C4、A5。
- 交付：固定输入 `9 + 6` 的 Agent 运行证据。
- 验收：`AgentResult.output.result == 15`，并检查 ModelRequest 摘要和 stop_reason。
- 关联：RD-002 + RD-001 回归；阶段 C 出口。

#### 6.6.4 阶段 D：Tool Call 闭环

目标：让真实模型产生 Tool Call，并完成校验、执行、结果回传和最终回答。

##### D1：定义 Tool、ToolInput 与 ToolResult

- 学习问题：外部动作需要哪些稳定声明和结果语义。
- 前置依赖：C5、A2。
- 交付：Tool 定义、输入、结果和错误协议。
- 验收：输入输出结构化，Tool 不包含推理和 Workflow 路由。
- 关联：K-002、K-003。

##### D2：实现 Tool Schema 校验

- 学习问题：模型产生的参数为什么不能直接执行。
- 前置依赖：D1。
- 交付：输入 Schema、输出 Schema 和 validation 错误。
- 验收：缺字段、错误类型和非法输出均确定性失败。
- 关联：K-002、K-003。

##### D3：实现允许工具解析与调用

- 学习问题：Agent 如何把模型 Tool Call 映射到允许能力。
- 前置依赖：D2、C3。
- 交付：allowed Tools 查找、未知 Tool 错误和调用入口。
- 验收：只能调用 AgentDefinition 中声明的 Tool。
- 关联：K-002、K-003。

##### D4：实现 Tool Result 回传 Model

- 学习问题：Tool Call 为什么是一个多轮模型循环。
- 前置依赖：D3。
- 交付：ToolResult 加入后续 ModelRequest，直到最终回答。
- 验收：事件顺序为 Model -> Tool -> Model，循环受 C4 上限约束。
- 关联：K-002。

##### D5：实现权限、超时与幂等声明

- 学习问题：Tool 如何成为可治理动作而不是普通函数调用。
- 前置依赖：D2。
- 交付：权限、超时、取消和幂等元数据。
- 验收：拒绝和超时具有明确错误；本任务不自动实现 Retry。
- 关联：K-003；RD-010、RD-012 的前置能力。

##### D6：完成 RD-003 Tool Call 验收

- 学习问题：真实模型能否通过统一协议选择并使用 Tool。
- 前置依赖：D4、D5、Provider Tool Choice 能力。
- 交付：`37 + 58` 的真实 Tool Call 证据。
- 验收：Tool 名称、参数、ToolResult `95`、事件顺序和最终结果正确。
- 关联：RD-003 + RD-001 至 RD-002 回归；阶段 D 出口。

#### 6.6.5 阶段 E：Memory 跨运行上下文

目标：实现由 Agent 决定读写、Memory 保证 scope 隔离的两轮上下文链路。

##### E1：定义 Memory Contract 与 MemoryItem

- 学习问题：跨运行记忆与运行上下文、WorkflowState 有何区别。
- 前置依赖：D6、A2。
- 交付：read、write、search、scope 和 MemoryItem 来源协议。
- 验收：MemoryItem 可序列化，不包含 Workflow 流程位置。
- 关联：K-006、K-010。

##### E2：实现 In-memory Memory Adapter

- 学习问题：如何用最小实现验证 Memory 协议而不提前引入数据库。
- 前置依赖：E1。
- 交付：可替换的内存读写和搜索实现。
- 验收：共享 Memory Contract Test 通过。
- 关联：K-006。

##### E3：实现 scope 隔离

- 学习问题：为什么跨会话和跨用户状态必须显式隔离。
- 前置依赖：E2。
- 交付：scope 读写和搜索边界。
- 验收：同 scope 可读，跨 scope 不可见。
- 关联：K-006、RD-004。

##### E4：实现 Agent Memory 读取策略

- 学习问题：MemoryItems 如何参与当前 ModelRequest。
- 前置依赖：E3、C2。
- 交付：Agent 按 Memory Policy 发起 read/search 并选择上下文。
- 验收：ModelRequest 可追踪使用了哪些 MemoryItems。
- 关联：K-006。

##### E5：实现 Agent Memory 写入策略

- 学习问题：谁决定什么值得记忆以及如何记录来源。
- 前置依赖：E4。
- 交付：Agent 创建 MemoryItem 并调用 Memory.write。
- 验收：MemoryItem 包含当前运行来源，不由 Memory Adapter 自动推断。
- 关联：K-006、RD-004。

##### E6：完成 RD-004 两轮对话验收

- 学习问题：跨运行上下文是否真正来自前序运行。
- 前置依赖：E5、A5。
- 交付：项目代号“青岚”的两轮真实对话证据。
- 验收：同 scope 召回、来源可追溯、跨 scope 隔离。
- 关联：RD-004 + RD-001 至 RD-003 回归；阶段 E 出口。

#### 6.6.6 阶段 F：Runtime 与 Execution

目标：把已完成的 Agent 链路纳入统一 Run 生命周期，并加入事件、流式、取消和执行治理。

##### F1：定义 RunRequest、RunContext 与 RuntimeResult

- 学习问题：运行状态、目标结果和业务输入为什么必须分离。
- 前置依赖：E6、A2。
- 交付：Run 请求、Context、RuntimeResult 和终态协议。
- 验收：RunContext 不替代 AgentInput、Memory 或 WorkflowState。
- 关联：K-005、K-008、K-010。

##### F2：实现 Runtime 生命周期与唯一终态

- 学习问题：如何保证一次 Run 只结束一次。
- 前置依赖：F1。
- 交付：started、running、completed、failed、cancelled、paused 状态转换。
- 验收：非法转换失败；每个 Run 只有一个终态。
- 关联：K-005、RD-005。

##### F3：实现 Events 与 Streaming

- 学习问题：过程增量和最终结果如何同时保持一致。
- 前置依赖：F2、B5。
- 交付：有序 Events、真实 Streaming 转发和最终合并。
- 验收：增量全部消费一次，顺序正确，合并结果一致。
- 关联：K-008、RD-008。

##### F4：实现 Cancellation 传播

- 学习问题：取消如何从 Runtime 到达 Model、Tool、Memory 和 Workflow。
- 前置依赖：F3。
- 交付：取消信号、下游停止和 cancelled 终态。
- 验收：取消后无新 chunk，不发送 completed。
- 关联：K-008、RD-009。

##### F5：实现 Hooks

- 学习问题：如何扩展生命周期而不修改 Core 职责。
- 前置依赖：F2。
- 交付：before/after 生命周期观察入口和顺序规则。
- 验收：Hook 顺序可断言，Hook 不能替换目标执行。
- 关联：K-008、RD-010。

##### F6：实现 Guardrails

- 学习问题：输入、模型输出和 Tool 调用如何被允许或拒绝。
- 前置依赖：F5、D5。
- 交付：允许路径、拒绝路径和结构化 policy 错误。
- 验收：拒绝后 Model/Tool 不被调用；允许路径继续真实执行。
- 关联：K-008、RD-010。

##### F7：实现 Retry 与幂等治理

- 学习问题：临时失败如何恢复而不重复副作用。
- 前置依赖：F2、D5。
- 交付：错误分类、有上限重试、attempt Events 和稳定幂等键。
- 验收：Schema、权限和取消不重试；幂等 Tool 只产生一次成功副作用。
- 关联：K-003、K-008、RD-012。

##### F8：完成 Runtime / Execution 真实验收

- 学习问题：运行治理能力能否在真实 Agent 链路中同时成立。
- 前置依赖：F3 至 F7。
- 交付：Runtime、Streaming、Cancellation、Hooks、Guardrails、Retry 真实证据。
- 验收：RD-005、RD-008、RD-009、RD-010、RD-012 全部通过。
- 关联：历史 RD-001 至 RD-004 回归；阶段 F 出口。

#### 6.6.7 阶段 G：Workflow 控制语义

目标：在 Runtime 之上实现可序列化、可恢复的确定性多步骤流程。

##### G1：定义 WorkflowDefinition、Input、State 与 Result

- 学习问题：流程定义、本次输入、运行状态和最终结果如何分离。
- 前置依赖：F8、A2。
- 交付：Workflow 四类公共协议和 Step 类型。
- 验收：Steps 属于 Definition，resume_token 不属于 WorkflowState。
- 关联：K-004、K-005。

##### G2：实现顺序步骤执行

- 学习问题：Workflow 如何保存步骤结果并推进流程位置。
- 前置依赖：G1。
- 交付：Agent、Tool 和 Function Step 的顺序调度。
- 验收：只执行当前可运行步骤，StepResult 可追踪。
- 关联：K-004。

##### G3：实现条件分支

- 学习问题：如何用结构化结果驱动确定性路径。
- 前置依赖：G2。
- 交付：Branch 条件、目标步骤和非法分支错误。
- 验收：只执行被选择分支。
- 关联：K-004、RD-006。

##### G4：实现暂停与恢复

- 学习问题：WorkflowState 和 Runtime resume_token 如何分治。
- 前置依赖：G2、F2。
- 交付：paused state、状态保存、token 校验后恢复。
- 验收：已完成有副作用步骤不重复，重复 token 无效。
- 关联：K-005、RD-007。

##### G5：实现无依赖步骤并行

- 学习问题：并行执行如何证明真实重叠并传播失败。
- 前置依赖：G2、F4。
- 交付：并行调度、结果合并、失败和取消传播。
- 验收：两个 step_started 早于任一完成，并覆盖失败路径。
- 关联：K-004、RD-011。

##### G6：完成 Workflow 真实验收

- 学习问题：Workflow 控制语义能否在真实 Agent 链路中成立。
- 前置依赖：G3 至 G5。
- 交付：分支、暂停恢复和并行真实证据。
- 验收：RD-006、RD-007、RD-011 全部通过。
- 关联：历史 RD-001 至 RD-005、RD-008 至 RD-010、RD-012 回归；阶段 G 出口。

#### 6.6.8 阶段 H：Kernel 累计验收与发布

目标：证明六个 Core、Execution、Adapter 和真实对话链路形成一致、可复核的 Kernel 基线。

##### H1：六个 Core Contract 累计回归

- 学习问题：具体实现是否真正遵守稳定公共协议。
- 前置依赖：G6。
- 交付：Model、Agent、Tool、Memory、Runtime、Workflow 共享合同证据。
- 验收：成功、失败、取消和序列化边界全部通过。
- 关联：K-001 至 K-008、K-010。

##### H2：Architecture Tests 与依赖扫描

- 学习问题：架构原则如何变成自动化约束。
- 前置依赖：H1。
- 交付：导入图、Provider 泄漏、业务反向依赖和旧入口检查。
- 验收：Core 不依赖 Application、Interface、SDK、数据库或旧项目。
- 关联：K-009。

##### H3：RD-001 至 RD-012 累计回归

- 学习问题：每个新增机制是否破坏了此前真实链路。
- 前置依赖：H2。
- 交付：12 个固定真实对话的完整证据集。
- 验收：全部 `PASS`；任何 `FAIL`、`BLOCKED` 或 `NOT RUN` 都阻止发布。
- 关联：K-010、RD-001 至 RD-012。

##### H4：发布首个完整架构版本

- 学习问题：如何把已验证实现固化为可审计架构事实。
- 前置依赖：H3。
- 交付：完整架构正文、版本入口和 changelog。
- 验收：架构文档与实现、Contracts、K/RD 证据一致，不重复调用 Provider。
- 关联：架构版本规则。

##### H5：完善 Kernel README 与学习记录

- 学习问题：如何让他人复现并解释本次框架学习成果。
- 前置依赖：H4。
- 交付：安装、配置、运行、测试、架构阅读和学习总结。
- 验收：新读者可按文档运行固定 Smoke 和查看证据，不依赖聊天记录。
- 关联：第一阶段最终交付。

### 6.7 交付里程碑

| 里程碑 | 完成阶段 | 可演示成果 |
|---|---|---|
| M0：实现准入 | A | 目录、类型、测试和证据基座全部确认 |
| M1：真实 Model | B | 固定请求通过统一协议调用真实 Provider |
| M2：最小 Agent | C | Agent 使用 Instructions 和 Model 完成真实任务 |
| M3：Tool Agent | D | 真实模型选择 Tool 并得到最终答案 |
| M4：有记忆 Agent | E | 两轮对话通过同 scope 召回前序信息 |
| M5：可治理 Run | F | 可观察、流式、取消、Guardrail 和 Retry |
| M6：Workflow | G | 可分支、暂停恢复和并行的流程 |
| M7：Kernel Baseline | H | 全部 K/RD 通过并发布首个架构版本 |

### 6.8 阶段门禁

```text
阶段 A 实现准入通过
  -> 阶段 B RD-001
  -> 阶段 C RD-002 + 历史 RD
  -> 阶段 D RD-003 + 历史 RD
  -> 阶段 E RD-004 + 历史 RD
  -> 阶段 F RD-005、RD-008 至 RD-010、RD-012 + 历史 RD
  -> 阶段 G RD-006、RD-007、RD-011 + 全部历史 RD
  -> 阶段 H Contract / Architecture / RD-001 至 RD-012
  -> 首个 Kernel 架构版本
```

门禁规则：

- 前置任务未完成，不得把后续任务标记为进行中。
- 阶段出口 RD 未通过，不得进入下一阶段。
- 历史 RD 回归失败，当前阶段退回未完成。
- Provider 能力阻塞时标记 `BLOCKED`，不得使用模拟结果绕过。
- H3 未全部通过，不得发布架构版本或声明 Kernel 完成。

### 6.9 进度与证据更新规则

每完成一个任务，同步更新：

1. 6.4 进度跟踪表中的任务状态。
2. 6.5 总体进度中的统计数字。
3. 对应 K/RD 的证据状态和可复现命令。
4. 当前 `DEV_SPEC.md` 和必要的版本增量文档。
5. 影响系统边界时的架构版本或 changelog。

任务详细实施文件、类、方法和测试节点由确认后的实施计划维护。实施计划必须引用本章任务 ID，不能新增本章未确认的架构决定。

任务分支遵循以下门禁：

```text
最新 architecture
  -> 创建仅承载一个任务的独立分支
  -> 在任务分支逐项确认设计
  -> 在任务分支实现并验证
  -> 用户确认任务结果
  -> 勾选任务并创建原子提交
  -> 合并回 architecture
```

- 每个任务都必须从最新 `architecture` 创建新分支。
- 一个任务分支不能混入其他 `DEV_SPEC.md` 任务。
- 用户确认前，任务保持 `[~]` 或原状态，不得标记 `[x]`。
- 用户确认前，不得提交任务结果或合并回 `architecture`。
- 合并完成后，下一任务必须重新从最新 `architecture` 创建分支。

## 7. 从 Agent Kernel 到完整 Agent 系统

### 7.1 当前 Kernel 的能力边界

本项目第一阶段交付的是 **Agent Kernel**，不是完整业务 Agent 产品。

Kernel 负责提供：

```text
Agent 推理循环
Workflow 控制语义
Tool 调用与治理
Memory 读写协议
Model Provider 抽象
Runtime 生命周期
```

Kernel 完成后能够证明：

- 一次 Agent 运行可以被正确驱动。
- Model、Tool 和 Memory 可以通过公共契约协作。
- Workflow 可以顺序执行、分支、暂停和恢复。
- Streaming、Cancellation、Retry 和 Events 具备明确语义。
- 具体 Provider、存储和 Runtime 可以通过 Adapter 替换。

但它还不能证明项目已经是完整的业务 Agent 系统，因为当前阶段不包含：

- 明确的垂直业务问题和真实用户。
- 业务意图、槽位、规则与数据模型。
- RAG、业务检索、排序和领域知识。
- 用户反馈、业务指标和线上质量闭环。
- 单 Agent 与 Multi-Agent 的效果对照。
- 面向生产运行的持久化证据和 Benchmark。

因此，Kernel 是后续 Agent 系统的基础，不是最终成果。后续演进必须保持依赖方向：

```text
Interface
    ↓
Application
    ↓
Agent Kernel
    ↓
Adapter / Infrastructure
```

业务 Application 可以组合和验证 Kernel，但不能把业务意图、业务状态、Prompt、领域规则或 Multi-Agent 路由反向写入 Kernel。

### 7.2 第一阶段：演进为可复盘的 Agent Harness

Kernel 通过累计验收后，下一步不是立即增加多个 Agent，而是建立一套能够稳定运行、恢复、审计和比较的 **Agent Harness**。

Harness 不新增核心原语，而是在现有 Runtime、Memory、Events 和 Adapter 之上补齐三类工程能力。

#### 7.2.1 控制面：系统如何运行

```text
用户请求
  -> 创建 Run
  -> 构建 Context
  -> 调用 Agent / Workflow
  -> 执行 Tool
  -> 更新状态
  -> 判断继续、暂停或结束
  -> 输出 Result
```

需要逐步补充：

- 分区构建 Instructions、Memory、History、Tool Result 和当前请求。
- 为不同 Context 区域设置预算和裁剪顺序。
- 当前用户请求不得因上下文超限被静默截断。
- Tool 必须经过 Schema、权限、超时和审批边界。
- 每次运行必须有明确的步数、重试和停止条件。

#### 7.2.2 状态面：系统保存什么

必须分离四类状态：

| 状态 | 用途 | 所有者 |
|---|---|---|
| Session | 延续多轮交互 | Application / Interface |
| WorkflowState | 保存流程位置和步骤结果 | Workflow |
| Durable Memory | 保存跨运行仍然有效的上下文 | Memory |
| Checkpoint | 保存可恢复的运行快照 | Runtime |

恢复不能只是重新读取旧聊天记录。Runtime 恢复前必须校验：

- `resume_token` 是否有效且未消费。
- Checkpoint 是否属于当前 Run 和 Workflow。
- 已完成的副作用是否会被重复执行。
- 依赖的 Application、配置和外部资源是否仍然一致。
- 不可信或过期状态是否需要拒绝恢复。

#### 7.2.3 证据面：系统如何被验证

每次 Run 至少产生三类运行工件：

```text
runs/<run_id>/
  task_state.json
  trace.jsonl
  report.json
```

| 工件 | 职责 |
|---|---|
| `task_state.json` | 当前运行状态、步骤、尝试次数和停止原因 |
| `trace.jsonl` | 按时间记录模型、工具、状态和错误事件 |
| `report.json` | 汇总最终结果、usage、耗时和失败分类 |

运行工件不属于 Memory，也不能代替 WorkflowState。

#### 7.2.4 Benchmark 基线

Harness 必须建立可重复执行的 Benchmark Contract：

```text
固定任务
+ 固定输入与环境
+ 允许使用的 Tool
+ 最大步骤预算
+ 结果 Verifier
+ 预期工件
```

评测至少记录：

- `pass_rate`
- `latency`
- `token_usage`
- `tool_steps`
- `attempts`
- `failure_category`
- `resume_correctness`

真实 Provider 评测用于验证模型与系统的组合效果；确定性基线用于隔离 Runtime、Tool、Verifier 和运行工件是否正确。两者不能混成一个总分。

#### 7.2.5 阶段完成标准

只有满足以下条件，才能认为 Kernel 已演进为可复盘的 Agent Harness：

1. 每次运行都有唯一状态和明确终态。
2. 中断后可以恢复，且不会重复已完成副作用。
3. 上下文超限时有确定的预算和裁剪行为。
4. 模型和工具调用均能从 Trace 中还原。
5. 固定 Benchmark 可以重复运行和比较。
6. 所有量化结论都能追溯到运行工件。

### 7.3 第二阶段：构建首个垂直业务 Application

Agent Harness 稳定后，使用一个范围足够小、结果可以验证的真实业务场景构建首个 Application。

Application 的目的不是展示更多框架能力，而是验证 Kernel 是否能支撑真实业务闭环。

#### 7.3.1 业务准入条件

业务场景必须明确：

| 项目 | 必须回答 |
|---|---|
| 目标用户 | 谁会实际使用 |
| 核心问题 | 用户需要完成什么任务 |
| 输入边界 | 系统接受哪些请求 |
| 输出边界 | 系统承诺提供什么结果 |
| 数据来源 | 事实和业务数据来自哪里 |
| 风险边界 | 哪些结果不能直接生成或执行 |
| 成功指标 | 如何判断结果有效 |

不接受“万能助手”“通用问答”这类无法定义完成标准的场景。

第一版只选择少量高频任务，先形成可以运行、评估和复盘的小闭环。

#### 7.3.2 Application 运行链路

推荐的业务主链路为：

```text
用户请求
  -> 意图与结构化信息理解
  -> 置信度判断
  -> 信息不足时澄清
  -> 确定性业务路由
  -> 检索 / Tool / 业务规则
  -> Agent 生成结果
  -> Guardrail 校验
  -> 结果返回
  -> Trace 与反馈记录
```

LLM 主要负责：

- 理解自然语言。
- 提取结构化信息。
- 生成自然语言解释。
- 处理难以完全规则化的语义任务。

Application 和确定性代码负责：

- 业务状态。
- 权限和数据范围。
- 流程路由。
- 检索与排序。
- 风险决策。
- 结果合法性校验。

不能让模型直接修改业务状态或绕过 Tool 执行外部动作。

#### 7.3.3 意图、槽位与澄清

对于需要多轮收集信息的业务，Application 可以定义：

```text
Intent
Slot Schema
Confidence
Missing Fields
Clarification Policy
```

稳健理解不能只依赖一次 LLM 判断，可以根据业务需要组合：

- LLM 语义识别。
- 关键词或确定性规则。
- 数据字典和枚举校验。
- 置信度阈值。
- 低置信度澄清。
- 不可识别请求的安全兜底。

这些都是业务概念，只能存在于具体 Application 中。

#### 7.3.4 确定性业务流水线

需要事实、候选项或结构化业务数据时，优先采用：

```text
业务条件
  -> 候选召回
  -> 确定性过滤
  -> 排序
  -> Agent 解释
  -> 输出校验
```

模型不能凭空创造业务实体。生成结果引用的 ID、记录或候选项必须来自检索结果或 Tool 返回值，并经过白名单校验。

#### 7.3.5 Guardrail 与全链路 Fallback

每个模型调用点都必须定义失败行为：

| 环节 | 典型失败 | 降级方向 |
|---|---|---|
| 意图理解 | 超时、格式错误、低置信度 | 规则判断或进入澄清 |
| 信息提取 | 字段缺失、枚举非法 | Schema 校验并补问 |
| 结果生成 | 空结果、引用不存在 | 模板结果或重新生成 |
| 风险校验 | 结果不合规 | 拒绝、改写或人工确认 |
| 评估模型 | Judge 不可用 | 保留确定性指标 |

Fallback 必须可观测，不能静默伪装成正常成功。

#### 7.3.6 业务评估闭环

首个 Application 必须建立：

```text
真实运行
  -> Trace
  -> Bad Case 筛选
  -> 人工标注
  -> 离线评估
  -> Prompt / 规则 / 模型调整
  -> 回归验证
  -> 新版本运行
```

业务指标至少覆盖：

- 意图或任务识别正确率。
- 结构化字段正确率。
- Tool 或检索结果正确率。
- 幻觉与非法引用比例。
- Fallback 比例。
- 安全规则命中情况。
- 延迟和模型成本。
- 用户反馈或任务完成率。

#### 7.3.7 Application 与 Kernel 的边界

```text
Application 可以包含：
业务 Agent、Workflow、Tool、Prompt、Policy、Evals、数据模型

Application 不能：
修改 Kernel 原语职责
把业务状态塞入 Runtime
把 WorkflowState 当作业务数据库
把 Trace 当作 Memory
复制一套 Agent Framework
```

#### 7.3.8 阶段完成标准

首个 Application 只有满足以下条件才算完成：

1. 有明确用户、业务问题和范围边界。
2. 至少一条真实业务链路可以端到端运行。
3. 关键失败点具有可观察的 Fallback。
4. 业务实体和事实来源可以追溯。
5. 已建立固定评测集和量化指标。
6. 至少完成一次基于 Bad Case 的改进和回归。
7. 单 Agent 基线已经建立，为是否引入 Multi-Agent 提供对照。

### 7.4 第三阶段：用基线实验决定是否引入 Multi-Agent

Multi-Agent 不是默认架构，也不是项目完整度的证明。

首个业务 Application 必须先建立单 Agent 基线。只有发现明确的职责冲突、上下文污染、专业能力隔离或并行执行需求，并且拆分收益可以量化时，才允许演进为 Multi-Agent。

#### 7.4.1 新增 Agent 的准入条件

新增 Agent 至少需要满足以下多数条件：

| 判断项 | 要求 |
|---|---|
| 独立目标 | 可以用一句话说明该 Agent 对什么结果负责 |
| 独立 Instructions | 需要不同的角色约束或推理规则 |
| 独立 Tool 集合 | 需要限制其可执行动作和权限 |
| 独立上下文 | 不应读取其他任务的全部上下文 |
| 独立输出 | 能定义稳定的结构化结果 |
| 独立评估 | 可以单独测量正确率、成本和失败情况 |
| 独立演进 | 可以替换模型或策略而不影响其他 Agent |

仅仅因为 Prompt 很长、代码文件很大或希望项目显得复杂，不构成新增 Agent 的理由。

#### 7.4.2 Agent 与 Workflow 的边界

```text
Agent
  -> 对目标进行智能判断和生成

Workflow
  -> 决定哪个步骤何时执行
```

Multi-Agent 协作仍然由 Workflow 或 Application Orchestrator 控制：

```text
用户请求
  -> 任务识别
  -> Workflow 路由
  -> 专业 Agent 执行
  -> 结果校验与聚合
  -> 最终响应
```

Agent 不应自行发现其他 Agent、修改流程拓扑或控制全局运行状态。

#### 7.4.3 合理的拆分模式

**专业边界拆分**

```text
问题理解 Agent
  -> 领域处理 Agent
  -> 结果审核 Agent
```

适用于不同阶段需要明显不同的 Instructions、工具权限或评估标准。

**复合任务拆分**

```text
复合请求
  -> 子任务 A Agent
  -> 子任务 B Agent
  -> 聚合结果
```

适用于一个请求包含多个可独立处理的目标。

**无共享副作用的并行拆分**

```text
            -> Agent A ->
用户请求 ->              -> Aggregator
            -> Agent B ->
```

只有子任务相互独立、没有共享写入冲突时才允许并行。

#### 7.4.4 路由与置信度

路由层必须输出结构化决策：

```text
RouteDecision
  intent
  target_agents
  confidence
  reasons
  fallback_route
```

低置信度时应进入：

- 用户澄清。
- 默认单 Agent 路径。
- 确定性 Workflow。
- 人工确认。

不能让低置信度路由静默触发高风险 Agent 或 Tool。

#### 7.4.5 通信和上下文隔离

Agent 之间不直接共享任意内部状态，只传递明确的结构化结果：

```text
AgentResult
  output
  evidence
  confidence
  warnings
  usage
  stop_reason
```

每个 Agent 只获得完成自身目标所需的最小上下文。业务状态仍由 Application 管理，流程状态仍由 Workflow 管理，运行生命周期仍由 Runtime 管理。

#### 7.4.6 冲突处理与结果聚合

多个 Agent 输出可能出现：

- 事实冲突。
- 重复结果。
- 置信度差异。
- 部分任务失败。
- 安全判断不一致。

Application 必须预先定义聚合策略：

```text
结构化校验
  -> 证据优先级
  -> 冲突检测
  -> 去重与合并
  -> Guardrail
  -> 最终结果
```

聚合不能只依赖另一个 LLM 随意总结。涉及业务事实、权限和风险时，必须有确定性规则或人工确认。

#### 7.4.7 Multi-Agent Fallback

每条协作链路必须定义降级路径：

| 失败场景 | 降级行为 |
|---|---|
| 路由失败 | 回到默认 Agent 或澄清 |
| 单个 Worker 失败 | 返回部分结果或执行替代步骤 |
| 并行任务超时 | 取消未完成任务并标记缺失结果 |
| 输出冲突 | 规则裁决或人工确认 |
| 聚合失败 | 返回经过校验的原始结果 |
| 成本超过预算 | 降级为单 Agent 路径 |

#### 7.4.8 单 Agent 与 Multi-Agent 对照实验

必须使用同一组业务任务比较：

| 指标 | 判断目标 |
|---|---|
| 任务成功率 | 拆分是否提升结果质量 |
| 子任务遗漏率 | 复合请求是否处理更完整 |
| 幻觉率 | 专业上下文是否降低错误 |
| 延迟 | 多次调用带来的时间成本 |
| Token 和费用 | 拆分是否造成不可接受的成本 |
| 失败率 | 协作链路是否更脆弱 |
| 可定位性 | Bad Case 是否更容易归因 |
| 用户反馈 | 最终体验是否真实改善 |

只有收益超过新增的路由、通信、聚合、延迟和调试成本，Multi-Agent 才能成为正式架构。

#### 7.4.9 阶段完成标准

Multi-Agent 演进只有满足以下条件才算成立：

1. 已存在可重复运行的单 Agent 基线。
2. 每个 Agent 都有独立且必要的职责。
3. 路由、通信、聚合和失败策略已经明确。
4. 共享状态和副作用具有清晰所有者。
5. 单 Agent 与 Multi-Agent 使用同一评测集比较。
6. 质量收益和新增成本都有运行证据。
7. 即使部分 Agent 失败，系统仍能进入明确终态。

### 7.5 完整 Agent 系统的证据闭环

Agent 系统不能因为能够对话、接入模型或包含多个 Agent，就被认定为“完整”或“生产级”。

所有能力声明必须由可重复运行的任务、结构化指标和可追溯工件共同证明。

#### 7.5.1 三层评估体系

评估必须区分三个层级，避免把模型能力、Kernel 正确性和业务效果混成一个总分。

| 层级 | 评估对象 | 典型指标 |
|---|---|---|
| Kernel Evaluation | 公共契约与运行语义 | 生命周期、事件顺序、取消、恢复、幂等 |
| Harness Evaluation | Agent 运行控制与工程治理 | 上下文预算、Tool 步数、运行恢复、失败分类 |
| Application Evaluation | 真实业务结果 | 任务成功率、事实正确率、安全性、用户反馈 |

Multi-Agent 对照实验属于 Application Evaluation，不用于证明 Kernel 本身正确。

#### 7.5.2 运行证据链

每个评测结果必须能够追溯：

```text
Evaluation Result
  -> Benchmark Run
  -> report.json
  -> task_state.json
  -> trace.jsonl
  -> Model / Tool / Memory / Workflow Events
  -> 对应代码、配置和 Prompt 版本
```

至少记录：

- Kernel 和 Application 版本。
- Model Provider 与模型标识。
- Prompt 和业务规则版本。
- Benchmark 数据集版本。
- Tool 与外部数据版本。
- 运行配置和预算。
- `run_id`、时间和环境信息。
- 最终结果、停止原因和失败分类。

#### 7.5.3 失败分类

不能只记录成功或失败。至少区分：

```text
model_error
tool_error
validation_error
routing_error
retrieval_error
guardrail_rejection
context_overflow
step_limit
timeout
cancelled
invalid_resume
aggregation_error
business_rule_failure
```

失败分类必须来自稳定协议，不能依赖事后阅读自然语言日志猜测。

#### 7.5.4 Bad Case 闭环

每个失败或低质量结果都应进入统一处理流程：

```text
发现 Bad Case
  -> 定位 Trace 和运行版本
  -> 判断失败层级
  -> 补充固定测试或评测样本
  -> 修改 Kernel / Harness / Application
  -> 运行对应层级回归
  -> 与修改前结果比较
  -> 保留改进证据
```

修复不能只针对单个输入修改 Prompt，而不补充可重复验证的样本。

#### 7.5.5 线上观测与离线评估

两者职责不同：

| 能力 | 主要用途 |
|---|---|
| 在线 Observability | 定位单次请求发生了什么 |
| 离线 Evaluation | 判断一个版本整体是否变好 |
| 用户反馈 | 验证系统是否解决真实问题 |
| Benchmark | 在固定条件下比较版本 |
| Regression Test | 防止已确认行为退化 |

Trace 是评估输入之一，但 Trace 数量不代表系统质量。

#### 7.5.6 量化声明规则

任何效果声明都必须说明：

```text
使用了什么任务集
样本数量是多少
基线版本是什么
运行了多少次
使用了什么 Provider
成功标准是什么
失败样本有哪些
证据保存在哪里
```

以下表达不能在没有证据时使用：

- “工业级”
- “生产可用”
- “准确率显著提升”
- “Multi-Agent 效果更好”
- “恢复成功率 100%”
- “大幅降低成本”

可以准确描述为：

```text
在指定 Benchmark、Provider、配置和样本范围内，
观察到某项指标相对基线发生变化。
```

#### 7.5.7 发布门禁

一个版本只有同时满足以下条件才允许发布：

1. 对应层级的自动化测试通过。
2. 历史真实对话场景完成累计回归。
3. 固定 Benchmark 没有未经解释的退化。
4. 关键失败路径具有 Trace 和测试证据。
5. Prompt、模型、规则和数据版本可以追溯。
6. 已知限制明确记录。
7. 文档描述与实际实现和指标一致。

通过这一证据闭环，项目才能从“功能演示”逐步成长为可运行、可比较、可复盘和可持续改进的 Agent 工程。

### 7.6 暂不引入的复杂能力

项目按“先建立最小正确闭环，再根据证据增加复杂度”的原则演进。

没有明确需求、基线和验收方式的能力，不进入当前 Kernel，也不因为其他框架具备该功能而提前建设。

#### 7.6.1 暂不建设的平台能力

以下能力延后评估：

- Agent Registry。
- Workflow Registry。
- Tool Marketplace。
- 动态 Agent 发现。
- 自动生成 Workflow。
- 可视化 Agent 编排平台。
- 远程 Runtime 服务。
- 分布式任务调度。
- 多租户资源和权限系统。
- 面向外部开发者的插件生态。

这些能力会引入注册、发现、版本、权限、部署和兼容性问题，不属于理解 Agent 核心运行机制的必要条件。

#### 7.6.2 暂不建设的自主化能力

当前不允许 Agent：

- 自行创建或修改 Agent。
- 自行修改 Workflow 拓扑。
- 自行扩大 Tool 权限。
- 自行修改 Guardrail。
- 自行发布 Prompt 或业务规则。
- 在没有预算约束时无限规划。
- 在没有用户确认时执行高风险副作用。
- 将一次运行结果自动提升为长期可信 Memory。

所谓“自主”不能绕过 Runtime 生命周期、Tool 治理、Application 规则和人工审批。

#### 7.6.3 按业务需要引入的能力

以下能力不是 Kernel 默认组成部分，只在首个业务 Application 明确需要时接入：

| 能力 | 引入条件 |
|---|---|
| RAG | 业务答案依赖可追溯的外部知识 |
| 向量数据库 | 已证明语义检索优于简单检索或数据库查询 |
| MCP | 需要通过标准协议连接外部工具或数据 |
| 用户画像 | 业务需要跨会话个性化，且具有授权和更新规则 |
| 长期语义 Memory | 已定义写入、召回、过期和删除策略 |
| LLM Judge | 确定性指标无法覆盖主观质量维度 |
| Web Dashboard | Trace 和 Evaluation 已稳定，确有运营和排查需求 |
| 多模型路由 | 已有成本、延迟或能力差异的对照数据 |

不能为了让架构图更丰富而提前加入这些组件。

#### 7.6.4 复杂能力准入门禁

新增复杂能力前必须回答：

1. 当前真实问题是什么？
2. 现有六个原语为什么无法直接解决？
3. 它属于 Kernel、Harness、Application、Interface 还是 Infrastructure？
4. 最小实现范围是什么？
5. 引入后增加了哪些状态、失败和安全风险？
6. 使用什么基线证明它产生收益？
7. 不引入时系统是否仍能正确运行？
8. 如何测试、观测、降级和移除？

如果这些问题没有明确答案，该能力继续保持延后状态。

#### 7.6.5 最终演进原则

```text
先证明 Kernel 正确
  -> 再证明 Harness 可运行和可复盘
  -> 再证明 Application 解决真实业务问题
  -> 再用基线证明 Multi-Agent 的必要性
  -> 最后评估平台化和分布式能力
```

项目的专业度不来自模块数量，而来自：

- 边界清楚。
- 取舍有理由。
- 失败可处理。
- 行为可追踪。
- 结果可评估。
- 结论有证据。
