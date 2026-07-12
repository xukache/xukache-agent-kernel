# Agent Kernel

这是一个从空白起点重建的通用 Agent Kernel 项目。

当前分支不兼容、不迁移旧项目。旧项目完整保留在 `mvp` 和 `main`，不作为本项目的代码、协议、测试或文档来源。

## 当前状态

- 处于设计确认阶段。
- 核心原语：`Agent`、`Workflow`、`Tool`、`Memory`、`Model`、`Runtime`。
- 已确认 Execution 执行层：`Context`、`Hooks`、`Guardrails`、`Retry`、`Cancellation`、`Streaming`。
- Core、Execution、支撑协议、Applications 和 Interfaces 已完成设计确认。
- 当前完整开发规格：`DEV_SPEC v0.15`，已完成对抗性规格审查修订，待用户审查。
- 第一条纵向切片将直接接入真实 Model Provider，不使用模拟模型。
- 尚未创建 Kernel 实现代码。
- 尚未发布架构版本；架构版本将在第一条 Kernel 纵向切片和 Contract Tests 通过后建立。

## 阅读顺序

1. [`DEV_SPEC.md`](DEV_SPEC.md)
2. [`docs/dev-spec/README.md`](docs/dev-spec/README.md)
3. [`docs/architecture/README.md`](docs/architecture/README.md)
4. [`docs/superpowers/specs/`](docs/superpowers/specs/)

每个模块逐项确认后，才会进入实现计划和代码阶段。
