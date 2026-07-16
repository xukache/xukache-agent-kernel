# 架构演进规则

本分册用于在 Agent 辅助开发中持续检查文档、代码和测试是否偏离已确认架构。

## 变更分类

| 变更 | 必须更新 |
|---|---|
| 新增功能或改变公共行为 | `DEV_SPEC.md`，并追加开发规格版本记录 |
| 完成模块设计确认 | `docs/superpowers/specs/` 对应记录 |
| 改变原语、模块边界、依赖、数据所有权、外部接口或部署 | 新的完整架构版本正文 |
| 只调整架构文档组织或导航 | `docs/architecture/99-changelog.md` |
| 新增外部 Interface | `docs/api-contracts.md`，确认后增加领域契约 |
| 改变工程约定或测试基线 | `docs/backend-conventions.md` 和相关规格 |

计划文档只能拆解已确认设计，不能作为架构事实源。

## 每次任务的架构检查

开始前：

- 当前任务是否已经在 `DEV_SPEC.md` 确认。
- 是否需要先建立独立任务分支。
- 是否触及尚未确认的物理目录、类型字段或 Interface。
- 是否需要阅读现有模块确认记录或架构版本。

实现中：

- 是否新增了六个核心原语之外的“核心”概念。
- Kernel 是否导入了 Application、Interface、Provider SDK 或具体存储。
- Adapter 类型是否泄漏进公共 Schema。
- Definition、Input、State、Event、Result 的所有权是否混合。
- Agent、Workflow、Runtime 是否越权接管彼此的语义。
- Memory Policy 是否明确读取 scope、写入目标、授权、预算和提升规则。
- 错误、取消、重试、事件和敏感数据规则是否被保持。

完成前：

- `DEV_SPEC.md`、分册、代码、测试和任务状态是否一致。
- Contract、Integration、Architecture 和 RD 验证是否覆盖此次风险。
- 是否存在未声明的兼容层、旧入口或旧协议。
- 是否需要更新开发规格版本或创建架构版本。

## 漂移信号

出现以下情况必须暂停实现并回到设计确认：

- 新代码需要绕过 Protocol 才能工作。
- Core 必须认识具体 Provider 或 Backend 类型。
- 同一数据在多个模块都有可变所有权。
- 为方便调用而创建 UniversalInput、KernelResult、KernelState 或万能 metadata。
- WorkflowState 被放入 Memory，或通过回放 Event 猜测恢复。
- 通过共享 Memory Adapter、内容相似度或模糊 scope 隐式读取其他会话、用户或项目。
- 通过修改原 MemoryItem 的 scope 静默扩大可见范围，或丢失跨 scope 提升来源。
- Model 获得 Python callable，或 Tool 决定是否继续 Model 循环。
- Interface 开始承载 Agent、Workflow 或业务执行语义。
- 新目录或公开导入路径在 A3 确认前被创建。

## 版本判定

不是每次文档更新都发布架构版本。只有改变系统边界时，才按照 [`README.md`](README.md) 创建 `docs/architecture/versions/` 下的完整正文。已发布版本只读，修正通过新版本完成。
