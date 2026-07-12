# Agent Kernel Developer Specification

> 版本：0.3 — 文档结构、设计边界与版本维护规则
>
> 状态：新项目重构中，当前分支不继承旧项目事实源
>
> 当前架构主分支：`architecture`
>
> 文档目的：先冻结文档组织方式和设计边界，再逐个确认模块；本文件不包含具体实现代码。

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
- 逐模块确认、实现和验收的工作方式。
- 文档、测试和架构演进的组织方式。

本文件当前不覆盖：

- 工伤认定、劳动能力鉴定和待遇测算。
- 政策检索和业务知识库。
- 具体模型供应商和 Prompt 内容。
- CLI、TUI、HTTP API 的迁移实现。
- 任何具体代码接口和目录内部实现。

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

每个原语都必须能在不阅读业务代码的情况下解释清楚，并能使用 Fake 或最小实现独立测试。

### 2.5 运行过程可解释

运行结果不仅要能返回最终输出，还要能说明：

- 哪个 Agent 或 Workflow 被执行。
- 使用了哪些 Tool、Model 和 Memory。
- 哪一步成功、失败、暂停或取消。
- Adapter 产生的结果如何回到 Kernel。

具体 Trace 字段在后续观测设计中确认，不在本阶段增加新的核心原语。

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

- 具体 Model Provider。
- 具体 Memory 存储。
- 具体 Tool 注册方式。
- 具体 Workflow 编排库。
- 具体 Trace 存储。
- 具体 CLI、TUI 或 HTTP 框架。

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

Kernel 单元测试不得依赖工伤业务、真实模型、真实外部服务或具体界面。

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
ananhu_agent/
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

每个模块单独确认，统一使用以下文档结构：

1. 模块目标。
2. 核心职责。
3. 非职责。
4. 最小公开接口。
5. 依赖关系。
6. 生命周期。
7. 可替换点。
8. 错误边界。
9. 测试方案。
10. 与 VoltAgent 设计思路的对应关系。
11. 当前项目的迁移边界。
12. 用户确认记录。

只有完成确认的模块，才允许进入实现计划。

### 5.4 模块确认顺序

```text
Agent
  -> Tool
  -> Workflow
  -> Memory
  -> Model
  -> Runtime
  -> 支撑协议
  -> Applications
  -> Interfaces
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

在所有模块确认前，不创建或冻结以下平行核心名词：

```text
Orchestrator
Capability
Stage
Domain Core
Agent Context
```

如果未来确实需要这些名称，必须先说明它们为什么不能由现有六个原语表达，并记录确认结果。

---

## 6. 项目排期

### 6.1 阶段总览

| 阶段 | 目标 | 产出 | 状态 |
|---|---|---|---|
| 0 | 文档结构和边界冻结 | `DEV_SPEC.md`、六原语边界 | 进行中 |
| 1 | 逐个确认 Kernel 模块 | 模块设计记录和确认记录 | 待开始 |
| 2 | 实现最小 Kernel | 协议、Fake 实现、单元测试 | 待开始 |
| 3 | 实现 Runtime Adapter | Native Runtime 和差分验证 | 待开始 |
| 4 | 组合业务 Application | `applications/work_injury/` | 待开始 |
| 5 | 迁移 Interface 和观测能力 | CLI、TUI、Eval、Trace | 待开始 |

### 6.2 阶段门禁

每个阶段必须满足前一阶段的验收条件：

```text
文档结构确认
  -> 模块设计确认
  -> 实现计划确认
  -> Kernel 实现
  -> Runtime 验证
  -> 业务迁移
```

在用户确认完整设计前，不进入代码实现。

### 6.3 任务记录

每个实现任务单独记录：

- 基于哪个设计版本。
- 修改哪些边界。
- 通过哪些测试。
- 是否影响业务应用。
- 是否需要升级架构版本。

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

### 8.2 Agent

状态：待确认。

### 8.3 Tool

状态：待确认。

### 8.4 Workflow

状态：待确认。

### 8.5 Memory

状态：待确认。

### 8.6 Model

状态：待确认。

### 8.7 Runtime

状态：待确认。

### 8.8 支撑协议

状态：待确认。

只在六个原语的边界确认后补充必要内容，不单独扩张为新的核心抽象。

### 8.9 Applications

状态：待确认。

只描述业务如何组合 Kernel，不在 Kernel 中增加业务概念。

### 8.10 Interfaces

状态：待确认。

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

当新增功能、调整模块边界或改变运行方式时，在 `docs/dev-spec/versions/` 增加一份版本增量文档：

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

以下变化必须新增版本增量文档：

| 变化类型 | `DEV_SPEC.md` | `docs/dev-spec/versions/` | 架构版本 |
|---|---|---|---|
| 修正错别字、失效链接或不改变语义的表达 | 更新 | 不需要 | 不需要 |
| 新增不改变核心边界的实现功能 | 更新 | 新增 | 按影响决定 |
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
| 2026-07-12 | v0.4 | 新 Kernel 重构起点 | 清理旧代码、旧文档和旧计划，建立不兼容旧项目的全新开发规格基线 | 当前草案 |

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
