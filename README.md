# Agent Kernel

这是一个从空白起点重建的通用 Agent Kernel 项目。

当前分支不兼容、不迁移旧项目。旧项目完整保留在 `mvp` 和 `main`，不作为本项目的代码、协议、测试或文档来源。

## 当前状态

- 处于实现准入阶段。
- 核心原语：`Agent`、`Workflow`、`Tool`、`Memory`、`Model`、`Runtime`。
- 已确认 Execution 执行层：`Context`、`Hooks`、`Guardrails`、`Retry`、`Cancellation`、`Streaming`。
- Core、Execution、支撑协议、Applications 和 Interfaces 已完成设计确认。
- 当前完整开发规格：`DEV_SPEC v0.25`。第一至七章已确认学习目标、核心特点、技术决策、双轨验收、整体架构、8 个阶段 47 个任务的学习实施路线，以及从 Kernel 到完整 Agent 系统的演进路线。
- 阶段 A 的 A1、A2、A3、A4 已完成；下一任务是 A5 真实对话证据基座。
- 六个 Core 的语义级公共契约、Python 类型表达策略、`src/agent_kernel` 物理目录和公开导入路径已经确认。
- 第一条纵向切片将直接接入真实 Model Provider，不使用模拟模型。
- 每个模块实现任务都必须新增真实用户对话输入输出场景，并累计回归此前全部真实对话场景。
- 尚未创建 Kernel Core 实现代码；当前只有可安装、可导入的空包入口。
- 尚未发布架构版本；首个架构版本的准确创建时点仍在实现准入阶段逐项确认。

## 文档索引

| 文档 | 作用 | 是否可覆盖 |
|---|---|---|
| [`DEV_SPEC.md`](DEV_SPEC.md) | 当前完整开发规格 | 可以持续更新 |
| [`docs/architecture.md`](docs/architecture.md) | 技术架构导航、事实源和分册入口 | 可以持续更新 |
| [`docs/api-contracts.md`](docs/api-contracts.md) | 当前程序化公共契约和未来外部接口建档规则 | 可以持续更新 |
| [`docs/backend-conventions.md`](docs/backend-conventions.md) | Python 后端实现、边界和验证规范 | 可以持续更新 |
| [`docs/dev-spec/README.md`](docs/dev-spec/README.md) | 开发规格版本目录、维护规则和历史索引 | 可以持续更新 |
| [`docs/dev-spec/versions/`](docs/dev-spec/versions/) | 各版本新增和变更记录 | 已发布文档只读 |
| [`docs/architecture/README.md`](docs/architecture/README.md) | 架构版本规则入口 | 可以持续更新 |
| [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md) | 六个核心原语和逻辑分层摘要 | 可以持续更新 |
| [`docs/architecture/01-module-boundaries.md`](docs/architecture/01-module-boundaries.md) | 模块职责、所有权和依赖方向 | 可以持续更新 |
| [`docs/architecture/02-runtime-data-flow.md`](docs/architecture/02-runtime-data-flow.md) | Agent、Tool、Memory 和 Workflow 数据流 | 可以持续更新 |
| [`docs/architecture/03-public-contracts.md`](docs/architecture/03-public-contracts.md) | 公共类型、错误和状态策略摘要 | 可以持续更新 |
| [`docs/architecture/10-evolution-rules.md`](docs/architecture/10-evolution-rules.md) | 架构演进和 Agent 修改检查清单 | 可以持续更新 |
| [`docs/architecture/99-changelog.md`](docs/architecture/99-changelog.md) | 架构文档维护记录 | 可以持续更新 |
| [`docs/architecture/versions/`](docs/architecture/versions/) | 架构版本完整正文 | 已发布正文只读 |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | 模块、章节和阶段设计确认记录 | 当前设计阶段持续追加 |
| `docs/superpowers/plans/` | 已确认设计的后续实施计划；目录尚未创建 | 实现阶段按需创建 |

## 文档使用规则

1. `DEV_SPEC.md` 是当前完整开发规格的唯一主线入口。
2. `docs/architecture.md` 负责导航已确认架构，不复制完整规格。
3. `docs/api-contracts.md` 和 `docs/backend-conventions.md` 分别维护调用边界与工程约定。
4. 版本新增和变更记录放在 `docs/dev-spec/versions/`。
5. 模块、章节和阶段确认记录放在 `docs/superpowers/specs/`。
6. 改变系统边界时，进入实现前必须创建新的架构版本正文。
7. 实施计划只能拆解已经确认的设计，不能反向决定架构。
8. 未确认内容必须明确标记为“待确认”，不得创建对应代码目录。

## 任务分支流程

```text
最新 architecture
  -> 创建单任务分支
  -> 逐项确认设计
  -> 完成实现与验证
  -> 用户确认任务结果
  -> 勾选 DEV_SPEC 任务
  -> 原子提交
  -> 合并回 architecture
```

未经用户确认，不得在任务分支上提前勾选任务、提交任务结果或合并回 `architecture`。

## 阅读顺序

第一次进入项目时：

1. 阅读 `DEV_SPEC.md` 第 1 章，理解项目目标、边界和非目标。
2. 阅读第 2 章，理解 Kernel 的七项核心特点。
3. 阅读第 3 章，理解自研与复用边界、技术基线和延后决策。
4. 阅读第 4 章，理解确定性测试、真实对话和模块完成门禁。
5. 阅读第 5 章，理解整体架构、六个核心模块和四条数据流。
6. 阅读第 6 章，查看 8 个阶段、47 个任务、里程碑和当前进度。
7. 阅读第 7 章，理解 Kernel 后续如何演进为完整 Agent 系统。
8. 查看 [`docs/superpowers/specs/README.md`](docs/superpowers/specs/README.md)，确认模块和章节的设计状态。
9. 阅读 [`docs/architecture.md`](docs/architecture.md)，按任务进入对应架构分册。
10. 修改公共契约或 Python 工程时，分别阅读 [`docs/api-contracts.md`](docs/api-contracts.md) 和 [`docs/backend-conventions.md`](docs/backend-conventions.md)。
11. 修改规格或新增版本前，阅读 [`docs/dev-spec/README.md`](docs/dev-spec/README.md)。

每个模块逐项确认后，才会进入实现计划和代码阶段。
