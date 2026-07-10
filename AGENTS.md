# 项目规范

> 单一事实来源：
> - MVP 技术架构基线：`TECH_ARCHITECTURE_MVP.md`
> - 技术架构入口：`docs/architecture.md`
> - API 契约入口：`docs/api-contracts.md`
> - 后端开发规范：`docs/backend-conventions.md`
> - 架构演进规则：`docs/architecture/10-evolution-rules.md`
>
> 本文件只保留顶层索引、阅读顺序和强制约束。详细设计只在对应事实源维护。

## 项目形态

- 类型：工伤咨询领域的后端 Agent Harness，当前以 CLI 作为开发和验收入口。
- 当前阶段：MVP 离线闭环已实现，正在演进框架中立协议和 LangGraph 运行时。
- 技术路线：不使用 Dify；协议重构完成后以 LangGraph 作为目标默认工作流运行时，领域和应用核心不得依赖 LangGraph 类型。
- 环境管理：统一使用 `uv` 管理 Python、虚拟环境、依赖和命令运行。
- Python 版本：固定使用 Python 3.11，版本文件为 `.python-version`。
- 对外接口：当前没有 HTTP API、WebSocket 或前端；这只是当前交付边界，不是 Agent 内核的永久限制。
- 业务定位：面向工伤认定、劳动能力鉴定、待遇辅助测算和政策咨询。

## 修改前必读

| 改动类型 | 必读文档 |
|---|---|
| 架构、模块边界、运行时、数据模型 | `docs/architecture.md` 和对应架构分册 |
| 工作流、Agent、状态、恢复、异步边界 | `docs/architecture/02-agent-runtime.md` |
| Prompt、上下文、记忆和裁剪 | `docs/architecture/03-prompt-context.md` |
| Tool、模型、RAG、测算能力 | `docs/architecture/04-tools-models.md` |
| Trace、usage、badcase、eval | `docs/architecture/05-data-observability.md` |
| 后端代码、CLI、测试、配置 | `docs/backend-conventions.md` |
| HTTP / WebSocket / 外部接入 | `docs/api-contracts.md` |

## 强制约束

1. Agent 数量由独立目标、上下文、权限和评测边界决定，不以展示“多 Agent”为目的。当前四个 Agent 是 MVP 实现现状，不是永久架构边界。
2. 接入后，LangGraph 只负责节点调度、条件路由、中断恢复和必要的有限并行；业务状态、状态合并规则、错误语义和运行证据由项目协议定义。
3. `StateGraph`、`Command`、LangGraph message、channel 和 checkpoint 类型不得进入 domain、application、Agent、Tool、Prompt、Eval 公共协议。
4. Agent 保持无状态，只读取项目定义的输入并返回结构化结果，不直接修改共享状态。
5. Agent 不直接调用底层能力，必须经过统一能力执行网关；现有实现为 `ToolExecutor`，后续演进为框架中立的 `CapabilityGateway` 时须保持治理语义。
6. Agent 不直接拼接完整 prompt，必须经过 `PromptManager` 和 `ContextManager`。
7. Prompt 必须版本化、可评测、可回滚；上下文裁剪不得丢失当前请求、已确认关键事实和直接支撑结论的证据。
8. 工具、Prompt、上下文、模型调用、状态转换、校验和安全守卫必须写入项目自己的 trace。LangGraph/LangSmith 观测不能替代业务 trace。
9. checkpoint、task state、session/case memory 和 trace 必须职责分离，不得互相冒充事实来源或恢复数据。
10. 当前不实现 HTTP API、WebSocket 和前端；新增外部接口前必须先更新 `docs/api-contracts.md`。
11. 架构变更必须同步更新 `docs/architecture/99-changelog.md`。
12. Python 环境、依赖安装、测试和 CLI 运行必须通过 `uv`；不要新增 `pip install` 或 `python -m pytest` 作为主路径命令。
13. 关键代码模块必须写中文注释，说明职责、协议边界、关键流程和非显而易见的业务规则。
14. 已发布的架构版本文档不得原地覆盖。后续架构升级、模块边界调整或新增功能，必须基于当前版本复制并生成一份新的版本文档，保留旧版本用于审计和版本对比。

## 开发分支流程

- 当前版本分支作为集成分支，例如 MVP 阶段使用 `mvp`。
- 每个任务开发前必须从当前版本分支创建任务分支。
- 分支命名格式：`<版本号>-<feature>-<任务>`，统一使用小写英文、数字和短横线。
- 示例：`mvp-workflow-state-task-25`。
- 任务完成后先汇报改动范围、验证结果和待合并分支，等待用户确认。
- 用户确认后才允许提交 commit，并合并回当前版本分支。
- 合并后确认版本分支包含任务提交；发生冲突必须停止并让用户确认处理方式。
- 未经用户确认，不得合并到 `mvp`、`main`、`master` 或其他版本分支。

## 文档同步纪律

- 修改工作流、Agent 清单、状态协议、reducer 或 checkpoint 时，同步更新 `02-agent-runtime.md`。
- 修改 Prompt、上下文或记忆时，同步更新 `03-prompt-context.md`，并说明 eval 影响。
- 修改 Tool、模型、RAG 或测算能力时，同步更新 `04-tools-models.md`，并检查幂等和 trace 字段。
- 修改 trace、usage、badcase 或 eval 时，同步更新 `05-data-observability.md`。
- 新增 FastAPI、WebSocket 或其他外部接口时，先更新 `docs/api-contracts.md`，再创建领域契约分册。
- 新增前端后再创建 `docs/frontend-conventions.md`，不要提前创建空文档。

## 架构文档版本化流程

- `docs/architecture.md` 始终作为当前有效架构入口，只维护当前版本号、当前文档链接、阅读顺序和版本索引，不承载完整历史正文。
- 每次架构版本升级或新增影响系统边界的功能前，先读取当前版本文档，以它为基线生成新版本，不允许直接覆盖旧版本文件。
- 版本文档统一放在 `docs/architecture/versions/`，命名格式为 `v<版本号>-<主题>.md`，例如 `v0.3-langgraph-runtime.md`、`v0.4-production-rag.md`。
- 新版本文档必须包含：版本信息、基线版本、变更原因、完整架构、相对上一版本的差异、兼容性与迁移策略、任务计划入口、验收标准和已知限制。
- 新增功能如果改变工作流、状态协议、Agent/Capability 边界、数据模型、外部接口、部署方式、安全规则或观测评测口径，必须升级架构版本；仅修正错别字、失效链接或不改变语义的表达可以直接修订当前入口文档。
- 生成新版本后，同一变更必须更新 `docs/architecture.md` 的当前版本指向和版本索引，并在 `docs/architecture/99-changelog.md` 记录版本、日期、变更摘要和迁移影响。
- 对应开发任务计划也必须新建版本化文件，不覆盖上一版本计划；计划中要明确基于哪个架构版本以及依赖的上一任务状态。
- 旧版本只能增加“已废弃 / 已归档 / 被哪个版本替代”的元信息，不得修改其原始架构正文。
- Agent 开始架构或大功能任务前，必须先确认当前架构版本、目标版本和新文档路径；未完成版本化文档时不得直接进入实现。

## 本地命令

```bash
uv python pin 3.11
uv sync --extra dev
uv run pytest -v
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```
