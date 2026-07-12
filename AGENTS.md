# 项目规范

## 项目定位

- 当前分支是全新 Agent Kernel 重构项目。
- `mvp` 和 `main` 保留旧项目；当前分支不读取、不兼容、不迁移旧项目。
- 当前唯一完整开发规格：`DEV_SPEC.md`。
- 当前模块确认记录：`docs/superpowers/specs/`。
- 当前开发规格版本记录：`docs/dev-spec/versions/`。
- 当前架构版本规则：`docs/architecture/README.md`。

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

## 分支规则

- 当前架构主分支：`architecture`。
- 新任务从当前重构分支创建。
- 未经用户明确确认，不合并或推送到 `mvp`、`main` 或其他分支。

## 环境规则

- Python 固定 3.11，使用 `.python-version`。
- 新项目建立 Python 工程后，统一使用 `uv` 管理环境、依赖、测试和运行。
- 不从旧项目的 `pyproject.toml`、`uv.lock`、代码或测试恢复实现。
