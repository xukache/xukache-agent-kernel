# 项目规范

> 单一事实来源：
> - MVP 原始架构快照：`TECH_ARCHITECTURE_MVP.md`
> - 技术架构入口：`docs/architecture.md`
> - API 契约入口：`docs/api-contracts.md`
> - 后端开发规范：`docs/backend-conventions.md`
> - Agent 变更监控：`docs/architecture/10-evolution-rules.md`
>
> 本文件只保留顶层索引、Agent 阅读顺序和必须遵守的项目约束。不要在这里重复维护长篇架构细节。

## 项目形态

- 类型：后端型 Agent CLI 项目。
- 当前阶段：MVP 架构基线，尚未实现业务代码。
- 技术路线：不使用 Dify，基于 Agno 自研多 Agent 编排。
- 环境管理：统一使用 `uv` 管理 Python、虚拟环境、依赖安装和命令运行。
- Python 版本：固定使用 Python 3.11，版本文件为 `.python-version`。
- 当前入口形态：无前端、无 HTTP API、交互式 CLI 优先。
- 业务定位：安安虎工伤智能助手，面向工伤认定、劳动能力鉴定、待遇测算和政策咨询场景。

## 修改前必读

| 改动类型 | 必读文档 |
|---|---|
| 架构、模块边界、运行时、数据模型 | `docs/architecture.md` 和对应 `docs/architecture/` 分册 |
| Agent 编排、上下文、异步边界 | `docs/architecture/02-agent-runtime.md` |
| Prompt、上下文裁剪、Prompt 评测 | `docs/architecture/03-prompt-context.md` |
| Tool、模型、RAG、测算工具 | `docs/architecture/04-tools-models.md` |
| Trace、badcase、eval、运行证据 | `docs/architecture/05-data-observability.md` |
| 后端代码、CLI、测试、配置 | `docs/backend-conventions.md` |
| API / WebSocket / 小程序接入 | `docs/api-contracts.md`，并确认当前是否仍为“暂无公开 API” |

## 强制约束

1. MVP 只保留 4 个核心 Agent：`IntentRouterAgent`、`PolicyRAGAgent`、`DomainConsultationAgent`、`PaymentCalculationAgent`。
2. 不为了“多 Agent”展示而提前拆分工伤认定、劳动能力鉴定、参保认定等专项 Agent。
3. Agent 不直接调用底层工具，必须经过 `ToolExecutor`。
4. Agent 不直接拼接完整 prompt，必须经过 `PromptManager` 和 `ContextManager`。
5. Prompt 必须版本化、可评测、可回滚。
6. 工具、Prompt、上下文、模型调用、校验和安全守卫必须写入 trace。
7. MVP 允许 async I/O，但不做复杂异步任务平台、后台任务、并行 Agent 仲裁或 WebSocket 多路事件流。
8. 当前不做前端，不创建前端规范；当前不暴露 HTTP API，不创建 API 领域分册。
9. 架构变更必须同步更新 `docs/architecture/99-changelog.md`。
10. 每个开发任务必须遵守下方“开发分支流程”，不得直接在版本分支上开发并提交。
11. Python 环境、依赖安装、测试和 CLI 运行必须通过 `uv` 执行；不要新增 `pip install`、`python -m pytest` 作为主路径命令。
12. 关键代码模块必须写中文注释，重点说明模块职责、核心协议边界、关键流程和非显而易见的业务规则；避免对简单字段或显而易见语句做机械注释。

## 开发分支流程

- 当前版本分支作为集成分支，例如 MVP 阶段使用 `mvp`。
- 每进行一个任务开发前，必须先从当前版本分支创建任务分支。
- 任务分支命名格式：`<版本号>-<feature>-<任务>`。
- 分支名统一使用小写英文、数字和短横线；中文任务名需要转成简短英文。
- 示例：从 `mvp` 分支开发 CLI 骨架任务时，创建 `mvp-cli-bootstrap-task-01`。
- 任务完成后，先向用户汇报改动范围、验证结果和待合并分支，等待用户确认。
- 用户确认没有问题后，才允许在任务分支提交 commit，并合并回当前版本分支。
- 合并完成后，应确认当前版本分支包含该任务提交；如有冲突，必须停止并让用户确认处理方式。
- 未经用户确认，不得把任务分支合并到 `mvp`、`main`、`master` 或其他版本分支。

## 文档同步纪律

- 修改 Agent 清单、上下文协议、Prompt 结构、Tool 注册、数据模型、评测指标时，同步更新对应架构分册。
- 修改 Prompt 时，同步更新 `docs/architecture/03-prompt-context.md`，并说明是否需要新增 eval case。
- 修改 Tool 时，同步更新 `docs/architecture/04-tools-models.md`，并检查 trace 字段是否仍完整。
- 修改运行证据、badcase、eval 字段时，同步更新 `docs/architecture/05-data-observability.md`。
- 如果新增 FastAPI、WebSocket 或小程序接口，必须先更新 `docs/api-contracts.md`，再创建 `docs/api-contracts/` 领域分册。
- 如果新增前端，再创建 `docs/frontend-conventions.md`，不要提前创建空文档。

## 本地命令

当前项目尚未初始化 Python 包。实现阶段必须使用 `uv` 和 Python 3.11：

```bash
uv python pin 3.11
uv sync --extra dev
uv run pytest -v
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```
