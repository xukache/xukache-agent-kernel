# 技术架构总纲

本文是安安虎工伤智能助手 Agno 多 Agent 重构版的技术架构入口。

当前项目处于 MVP 架构基线阶段，尚未实现业务代码。`TECH_ARCHITECTURE_MVP.md` 是 MVP v0.1 原始设计快照；`docs/architecture/` 是后续实现和迭代时的长期维护事实源。

## 文档状态

- 当前阶段：无前端交互式 CLI MVP。
- 当前实现：仅有架构文档，尚未创建 Python 包结构。
- 环境管理：使用 `uv`，Python 版本固定为 3.11。
- API 状态：当前不暴露 HTTP API，详见 `docs/api-contracts.md`。
- 架构事实源优先级：
  1. 当前代码决定实际表现。
  2. `docs/architecture/` 决定长期维护架构事实。
  3. `TECH_ARCHITECTURE_MVP.md` 保留为 MVP 原始设计快照。
  4. API 契约以 `docs/api-contracts.md` 为入口。

## 阅读顺序

| 顺序 | 文档 | 目的 |
|---|---|---|
| 1 | `docs/architecture/00-overview.md` | 理解项目定位、MVP 范围和非目标 |
| 2 | `docs/architecture/01-business-flow.md` | 理解业务流程、数据流和 badcase 回流 |
| 3 | `docs/architecture/02-agent-runtime.md` | 理解 Agent 编排、上下文协议和异步边界 |
| 4 | `docs/architecture/03-prompt-context.md` | 理解 PromptManager、ContextManager、prompt 评测和回滚 |
| 5 | `docs/architecture/04-tools-models.md` | 理解 ToolExecutor、ToolRegistry、ModelRouter 和多模型策略 |
| 6 | `docs/architecture/05-data-observability.md` | 理解 TaskState、Trace、Report、Badcase 和 Eval |
| 7 | `docs/architecture/10-evolution-rules.md` | 理解架构演进和 Agent 变更监控 |
| 8 | `docs/architecture/99-changelog.md` | 查看架构变更记录 |

## 核心原则

1. MVP 只保留 4 个核心 Agent，不按业务名词提前拆 Agent。
2. Orchestrator 持有状态，Agent 无状态执行。
3. 工具由 `ToolExecutor` 统一治理，模型不能直接触碰业务工具。
4. Prompt 是工程资产，必须版本化、分区、可评测、可回滚。
5. Trace、TaskState、Report 是系统证据链，不是附属日志。
6. 当前只做 CLI，同步主流程；允许 async I/O，但不做复杂异步任务平台。

## 不适用项

- 当前无前端，不启用前端架构分册。
- 当前无 HTTP API，不启用 API 领域契约分册。
- 当前不接 MCP / Skill 平台化扩展。
- 当前不接语音、图片、多模态输入。
- 当前不做复杂 checkpoint / resume、后台任务、并行 Agent 仲裁。

## 维护规则

- 本文件只做索引和顶层原则，不放长篇模块细节。
- 修改系统模块边界、Agent 清单、上下文协议、Prompt 管理、Tool 管理、数据模型、评测指标时，必须同步更新对应分册。
- 架构级变更必须更新 `docs/architecture/99-changelog.md`。
- Agent 变更监控统一写入 `docs/architecture/10-evolution-rules.md`，不创建 `docs/agent-monitoring.md`。
