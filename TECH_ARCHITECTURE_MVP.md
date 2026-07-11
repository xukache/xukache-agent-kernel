# 安安虎工伤智能助手技术架构版本入口

> 本文件是稳定入口，不再承载可被覆盖的完整架构正文。
>
> 当前有效版本：[`v0.9-direct-knowledge-capability.md`](docs/architecture/versions/v0.9-direct-knowledge-capability.md)

## 当前版本

| 字段 | 内容 |
|---|---|
| 架构版本 | v0.9 |
| 发布日期 | 2026-07-11 |
| 基线 | v0.8 KnowledgeGateway policy baseline |
| 技术路线 | 框架中立业务内核 + 双运行时 + CapabilityGateway + KnowledgeGateway lexical baseline |
| 完整正文 | `docs/architecture/versions/v0.9-direct-knowledge-capability.md` |
| 演进计划 | `docs/superpowers/plans/2026-07-11-direct-knowledge-capability-v0.9.md` |

## 版本索引

| 版本 | 状态 | 文档 | 说明 |
|---|---|---|---|
| v0.9 | 当前有效 | `docs/architecture/versions/v0.9-direct-knowledge-capability.md` | 直接 KnowledgeCapability、能力治理和旧兼容层删除 |
| v0.8 | 已归档 | `docs/architecture/versions/v0.8-knowledge-gateway-policy-baseline.md` | KnowledgeGateway、可信政策语料和 lexical RAG baseline |
| v0.7 | 已归档 | `docs/architecture/versions/v0.7-textual-chat-tui.md` | 框架中立实时运行事件与 Textual Chat TUI |
| v0.6 | 已归档 | `docs/architecture/versions/v0.6-model-catalog.md` | Provider/Profile 模型目录与按模型档位路由 |
| v0.5 | 已归档 | `docs/architecture/versions/v0.5-real-model-gateway.md` | 框架中立 ModelGateway 与 OpenAI-compatible provider |
| v0.4 | 已归档 | `docs/architecture/versions/v0.4-runtime-differential.md` | Native/LangGraph 双运行时差分验收 |
| v0.3 | 已归档 | `docs/architecture/versions/v0.3-langgraph-runtime.md` | 最小串行 LangGraph Runtime |
| v0.2 | 已归档 | `docs/architecture/versions/v0.2-framework-neutral-baseline.md` | 框架中立化与 LangGraph 演进基线 |

## 发布规则

1. 架构升级时，基于当前版本正文创建新的 `docs/architecture/versions/v<版本号>-<主题>.md`。
2. 新版本正文必须完整自洽，不能只记录差异；差异同时写入版本文档和 `docs/architecture/99-changelog.md`。
3. 新版本评审通过后，更新本文件的当前版本、版本索引和演进计划入口。
4. 已发布版本正文只读。只能追加归档状态和替代版本元信息，不能重写原始架构内容。
5. `docs/architecture/` 分册是当前架构的主题化事实源；版本快照用于审计、对比和恢复历史上下文。发布新版本时二者必须同步。

## 阅读顺序

1. 本文件确认当前架构版本。
2. 阅读当前版本完整正文。
3. 阅读 `docs/architecture.md` 和相关主题分册。
4. 阅读当前版本对应的实施计划。
5. 使用 `docs/architecture/99-changelog.md` 查看跨版本变更摘要。
