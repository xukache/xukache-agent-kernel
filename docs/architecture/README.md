# 架构版本目录

当前完整架构版本为
[`v0.1-memory-scope-sharing`](versions/v0.1-memory-scope-sharing.md)，冻结六个核心原语、
单向依赖和 Memory scope、隔离与跨会话共享语义。

技术架构总入口是 [`docs/architecture.md`](../architecture.md)。本文件只负责架构版本的创建、命名和只读规则，不能替代当前完整规格或架构分册。

## 当前架构分册

| 文档 | 作用 |
|---|---|
| [`00-overview.md`](00-overview.md) | 逻辑分层和六个核心原语 |
| [`01-module-boundaries.md`](01-module-boundaries.md) | 模块职责、所有权和单向依赖 |
| [`02-runtime-data-flow.md`](02-runtime-data-flow.md) | Agent、Tool、Memory 和 Workflow 数据流 |
| [`03-public-contracts.md`](03-public-contracts.md) | 公共类型和序列化边界 |
| [`10-evolution-rules.md`](10-evolution-rules.md) | 架构变更监控和文档同步 |
| [`99-changelog.md`](99-changelog.md) | 架构文档维护记录 |

## 版本规则

当确认的设计改变以下内容时，创建新的完整架构版本：

- Kernel 原语或模块边界。
- 依赖方向和运行链路。
- 数据模型、持久化或恢复方式。
- 外部接口或部署方式。
- 安全、观测或测试验收口径。

版本文件放在：

```text
docs/architecture/versions/
  v<版本号>-<主题>.md
```

每份版本正文必须包含：

1. 版本信息。
2. 基线版本。
3. 变更原因。
4. 完整架构。
5. 相对上一版本的差异。
6. 兼容性和迁移策略。
7. 任务计划入口。
8. 验收标准。
9. 已知限制。

## 与开发规格的关系

- `DEV_SPEC.md` 永远维护当前完整开发规格。
- `docs/dev-spec/versions/` 记录每个开发规格版本的新增和变化。
- `docs/architecture/versions/` 记录改变系统边界后的完整架构快照。
- 三类文档必须互相链接，不能用计划文档代替架构事实。
- 只改变文档组织而不改变系统边界时，更新 `99-changelog.md`，不创建架构版本正文。

## 当前事实源

1. 当前完整规格以 `DEV_SPEC.md` 为准。
2. 当前架构事实由架构分册和最新完整架构版本共同表达。
3. 模块确认理由以 `docs/superpowers/specs/` 为准。
4. 未确认内容不得进入实现。

## 版本索引

| 版本 | 主题 | 状态 |
|---|---|---|
| [`v0.1`](versions/v0.1-memory-scope-sharing.md) | Memory scope、会话隔离与跨会话共享 | 当前完整架构基线 |
