# 项目规范

## 项目定位

- 当前分支是全新 Agent Kernel 重构项目。
- `mvp` 和 `main` 保留旧项目；当前分支不读取、不兼容、不迁移旧项目。
- 当前属于“已有设计、尚无 Kernel 实现代码”的 Python 后端/库项目。
- 当前唯一完整开发规格：`DEV_SPEC.md`。
- 当前技术架构入口：`docs/architecture.md`。
- 当前公共接口契约入口：`docs/api-contracts.md`。
- 当前后端工程规范：`docs/backend-conventions.md`。
- 当前模块确认记录：`docs/superpowers/specs/`。
- 当前开发规格版本记录：`docs/dev-spec/versions/`。
- 当前架构版本规则：`docs/architecture/README.md`。

## 修改前阅读顺序

1. 阅读 `DEV_SPEC.md` 中与任务相关的章节和任务状态。
2. 阅读 `docs/architecture.md`，确认事实源优先级和对应架构分册。
3. 涉及公共类型、调用边界或外部接口时，阅读 `docs/api-contracts.md`。
4. 涉及 Python 工程、依赖、异步、错误或测试时，阅读 `docs/backend-conventions.md`。
5. 涉及系统边界或长期演进时，阅读 `docs/architecture/10-evolution-rules.md` 和 `docs/architecture/README.md`。

## 核心边界

核心只保留：

```text
Agent
Workflow
Tool
Memory
Model
Runtime
```

业务应用以后放在 `applications/`，不能反向进入 Kernel。第三方模型、存储、运行时和接口只能通过适配器接入。

## 强制约束

1. 每个模块必须逐项展示并获得用户确认后才能实现。
2. 未确认设计不得创建对应代码目录。
3. 不兼容旧项目，不保留旧模块别名、旧数据协议或旧入口。
4. 新增功能先更新完整 `DEV_SPEC.md`。
5. 每个版本的新增和变更追加到 `docs/dev-spec/versions/`。
6. 改变系统边界时，必须创建新的 `docs/architecture/versions/` 完整正文。
7. 计划文档只描述已确认设计的实现任务，不能反向决定架构。
8. 关键代码和协议必须有中文注释，说明职责和边界。
9. 提交前运行与变更匹配的验证；未验证不得声称完成。
10. 新增文档必须链接到现有事实源，不得复制并形成第二份完整规格。

## 分支规则

- 当前架构主分支：`architecture`。
- 每个任务必须从最新 `architecture` 创建独立任务分支。
- 一个任务分支只承载一个 `DEV_SPEC.md` 任务，不混入其他任务。
- 不对应 `DEV_SPEC.md` 实施编号的纯文档治理任务也必须使用独立任务分支，但不得修改实施任务状态。
- 任务设计、实现和验证都在对应任务分支完成。
- 用户确认任务结果后，才允许勾选任务、提交并合并回 `architecture`。
- 未经用户确认，不得提前勾选、提交或合并任务分支。
- 未经用户明确确认，不合并或推送到 `mvp`、`main` 或其他分支。

## 环境规则

- Python 固定 3.11，使用 `.python-version`。
- 新项目建立 Python 工程后，统一使用 `uv` 管理环境、依赖、测试和运行。
- 不从旧项目的 `pyproject.toml`、`uv.lock`、代码或测试恢复实现。
