# 技术架构总纲

本文是安安虎工伤智能助手 Agent Harness 的架构事实源入口。

## 文档状态

- 当前阶段：最小串行 LangGraph 运行时已接入，Native Runtime 保留用于回归。
- 当前架构版本：v0.3，完整快照见 `architecture/versions/v0.3-langgraph-runtime.md`。
- 当前运行时：默认 `LangGraphWorkflowRuntime`，通过 `WorkflowRuntime` 端口调用；可显式选择 `NativeWorkflowRuntime`。
- 演进方向：在框架中立协议下逐步扩展真实模型、知识和差分验收。
- 核心原则：领域、应用、Agent、Capability、Trace 和 Eval 协议不依赖 LangGraph。
- 外部接口：当前只有 CLI；没有 HTTP API、WebSocket 或前端。
- 架构版本入口：`TECH_ARCHITECTURE_MVP.md`。

## 事实源优先级

1. 对应 `docs/architecture/` 分册中的当前规则。
2. `docs/architecture/99-changelog.md` 中较新的架构决策。
3. `TECH_ARCHITECTURE_MVP.md` 指向的当前只读版本正文。
4. 实施计划只作为执行历史，不覆盖当前架构事实。

## 阅读顺序

| 顺序 | 文档 | 关注内容 |
|---|---|---|
| 1 | `00-overview.md` | 项目定位、分层、范围和非目标 |
| 2 | `01-business-flow.md` | 稳定业务阶段和数据流 |
| 3 | `02-agent-runtime.md` | 状态、运行时端口、LangGraph 边界和恢复 |
| 4 | `03-prompt-context.md` | Prompt、上下文、案件事实和记忆 |
| 5 | `04-tools-models.md` | 能力执行、模型、知识检索和幂等 |
| 6 | `05-data-observability.md` | Trace、Usage、Badcase 和 Eval |
| 7 | `10-evolution-rules.md` | 架构演进与同步规则 |
| 8 | `99-changelog.md` | 架构变更记录 |

完整历史版本统一保存在 `docs/architecture/versions/`，当前主题分册与当前版本正文必须保持一致。

## 核心原则

1. LangGraph 是调度运行时，不是业务架构。
2. 工作流按稳定业务阶段建模，不按 Agent 名称机械建图。
3. 项目协议定义业务状态、状态增量、reducer、停止原因、错误码和运行证据。
4. Agent 无状态，不直接修改共享状态、调用底层能力或拼接完整 Prompt。
5. 当前四 Agent 是实现现状，不是永久架构约束。
6. checkpoint、审计快照、session/case memory 和 trace 职责分离。
7. Native 与 LangGraph Runtime 必须通过同一套 contract tests 和 eval 数据。
8. 所有框架、模型、检索库和存储实现都通过端口隔离。

## 当前不适用项

- 当前不启用 HTTP / WebSocket 领域契约分册。
- 当前不建设前端规范。
- 当前不启用复杂并行 Agent 仲裁、通用工作流平台和多路流式协议。
- 当前不宣称 fake model、fixture RAG 或未启用 checkpoint 的能力已经生产可用。

这些是阶段边界，不是 Agent 内核的永久限制。

## 维护规则

- 模块边界、状态协议、运行时所有权、事件、权限或评测变化时，同步更新对应分册。
- 架构级变化必须记录在 `99-changelog.md`。
- API 状态变化先更新 `docs/api-contracts.md`。
- 不在 README、AGENTS 和实施计划中重复维护详细架构；只写摘要并链接事实源。
