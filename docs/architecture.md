# 技术架构

本文档是 Agent Kernel 技术架构的导航入口。它不替代 `DEV_SPEC.md`，也不提前冻结尚未由后续 B-G 任务确认的具体字段和实现细节。

## 当前状态

- 六个核心原语、Execution 支撑能力、逻辑分层、公共类型策略和 A3 物理目录已经确认。
- 当前尚未创建 Kernel 实现代码。
- A3 已确认 `src/agent_kernel` 为 Kernel 包和公开导入路径基线。
- 当前没有对外 HTTP、REST、WebSocket 或 MCP 接口。
- 第一阶段通过 Python Programmatic Interface 和测试组合根调用 Kernel。

## 事实源优先级

发生描述差异时，按以下顺序判断：

1. [`DEV_SPEC.md`](../DEV_SPEC.md)：当前完整开发规格和实施进度。
2. [`docs/superpowers/specs/`](superpowers/specs/)：已确认模块和任务的设计证据。
3. 本目录下的架构分册：对已确认逻辑结构的导航和摘要。
4. 后续实现代码与测试：已经落地行为的证据，但不能绕过规格变更流程自行改变架构。

架构分册不得引入 `DEV_SPEC.md` 未确认的新原语、依赖方向或公共协议。

## 阅读顺序

| 文档 | 解决的问题 |
|---|---|
| [`00-overview.md`](architecture/00-overview.md) | 系统由哪些逻辑层和核心原语组成 |
| [`01-module-boundaries.md`](architecture/01-module-boundaries.md) | 每个模块负责什么、依赖可以朝哪里 |
| [`02-runtime-data-flow.md`](architecture/02-runtime-data-flow.md) | Agent、Tool、Memory、Workflow 如何运行 |
| [`03-public-contracts.md`](architecture/03-public-contracts.md) | 行为、装配、数据、错误和状态用什么类型表达 |
| [`10-evolution-rules.md`](architecture/10-evolution-rules.md) | 变更时如何同步规格、文档、测试和版本 |
| [`99-changelog.md`](architecture/99-changelog.md) | 架构文档入口的变更记录 |

## 相关入口

- [`docs/api-contracts.md`](api-contracts.md)：当前程序化公共契约和未来接口建档规则。
- [`docs/backend-conventions.md`](backend-conventions.md)：Python 后端实现约定。
- [`docs/architecture/README.md`](architecture/README.md)：架构版本发布和只读规则。
- [`docs/dev-spec/README.md`](dev-spec/README.md)：开发规格版本维护规则。

## 维护规则

1. 功能或契约变更先更新 `DEV_SPEC.md`。
2. 已确认设计的摘要才可以进入架构分册。
3. 只改变文档组织、不改变系统边界时，更新 `99-changelog.md`，不创建架构版本正文。
4. 改变原语、模块边界、依赖、数据所有权、外部接口、部署或验收口径时，按 [`docs/architecture/README.md`](architecture/README.md) 创建完整架构版本。
5. A3 已确认物理目录基线；A4 负责建立工程，后续模块任务不得绕过已确认的公开入口。
