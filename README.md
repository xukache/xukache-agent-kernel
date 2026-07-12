# Agent Kernel

这是一个从空白起点重建的通用 Agent Kernel 项目。

当前分支不兼容、不迁移旧项目。旧项目完整保留在 `mvp` 和 `main`，不作为本项目的代码、协议、测试或文档来源。

## 当前状态

- 处于设计确认阶段。
- 核心原语：`Agent`、`Workflow`、`Tool`、`Memory`、`Model`、`Runtime`。
- 已确认 Execution 执行层：`Context`、`Hooks`、`Guardrails`、`Retry`、`Cancellation`、`Streaming`。
- Core、Execution、支撑协议、Applications 和 Interfaces 已完成设计确认。
- 当前完整开发规格：`DEV_SPEC v0.25`。第一至七章已确认学习目标、核心特点、技术决策、双轨验收、整体架构、8 个阶段 47 个任务的学习实施路线，以及从 Kernel 到完整 Agent 系统的演进路线。
- 阶段 A 的 A1 已完成，当前正在逐项确认 A2 公共类型表达策略。
- 六个 Core 的语义级公共契约已经冻结；整体架构表达已完成重构，具体 Python 类型表达和物理目录仍待逐模块确认。
- 第一条纵向切片将直接接入真实 Model Provider，不使用模拟模型。
- 每个模块实现任务都必须新增真实用户对话输入输出场景，并累计回归此前全部真实对话场景。
- 尚未创建 Kernel 实现代码。
- 尚未发布架构版本；首个架构版本的准确创建时点仍在实现准入阶段逐项确认。

## 文档索引

| 文档 | 作用 | 是否可覆盖 |
|---|---|---|
| [`DEV_SPEC.md`](DEV_SPEC.md) | 当前完整开发规格 | 可以持续更新 |
| [`docs/dev-spec/README.md`](docs/dev-spec/README.md) | 开发规格版本目录、维护规则和历史索引 | 可以持续更新 |
| [`docs/dev-spec/versions/`](docs/dev-spec/versions/) | 各版本新增和变更记录 | 已发布文档只读 |
| [`docs/architecture/README.md`](docs/architecture/README.md) | 架构版本规则入口 | 可以持续更新 |
| [`docs/architecture/versions/`](docs/architecture/versions/) | 架构版本完整正文 | 已发布正文只读 |
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | 模块、章节和阶段设计确认记录 | 当前设计阶段持续追加 |
| `docs/superpowers/plans/` | 已确认设计的后续实施计划；目录尚未创建 | 实现阶段按需创建 |

## 文档使用规则

1. `DEV_SPEC.md` 是当前完整开发规格的唯一主线入口。
2. 版本新增和变更记录放在 `docs/dev-spec/versions/`。
3. 模块、章节和阶段确认记录放在 `docs/superpowers/specs/`。
4. 改变系统边界时，进入实现前必须创建新的架构版本正文。
5. 实施计划只能拆解已经确认的设计，不能反向决定架构。
6. 未确认内容必须明确标记为“待确认”，不得创建对应代码目录。

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
9. 修改规格或新增版本前，阅读 [`docs/dev-spec/README.md`](docs/dev-spec/README.md)。

每个模块逐项确认后，才会进入实现计划和代码阶段。
