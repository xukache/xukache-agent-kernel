# 10. 架构演进与变更监控

本文定义架构演进、文档同步和 Agent 变更监控规则。Agent 监控不单独拆出 `docs/agent-monitoring.md`，统一在本文维护。

## 变更同步规则

- 修改 Agent 清单、职责、路由策略时，同步更新 `02-agent-runtime.md` 和 `99-changelog.md`。
- 修改 `AgentContext`、`AgentMessage`、槽位 schema 时，同步更新 `02-agent-runtime.md` 和 `05-data-observability.md`。
- 修改 Prompt 模板、版本策略、输出 schema、失败策略时，同步更新 `03-prompt-context.md`，并补充或调整 eval case。
- 修改 Tool 清单、ToolRegistry、ToolExecutor、错误码时，同步更新 `04-tools-models.md` 和 trace 字段。
- 修改模型配置、model profile 或模型选择策略时，同步更新 `04-tools-models.md`。
- 修改 task state、trace、report、badcase、eval 数据结构时，同步更新 `05-data-observability.md`。
- 新增 HTTP API、WebSocket 或小程序接口时，同步更新 `docs/api-contracts.md`，并创建 API 领域分册。
- 新增前端时，创建 `docs/frontend-conventions.md` 并补充前端架构分册。

## Agent 必须监控的变更类别

| 类别 | 需要检查 |
|---|---|
| Agent | Agent 数量、职责、路由、输入输出 schema |
| Prompt | prompt id/version、模板分区、failure policy、eval 指标 |
| Tool | 注册元信息、参数 schema、错误码、trace 字段 |
| Context | active slots、RAG evidence、recent turns、裁剪规则 |
| Model | provider、model profile、temperature、usage metadata |
| Data | task_states、agent_traces、run_reports、badcases、eval_cases |
| Runtime | CLI 入口、异步边界、fallback、safety guard |
| API | 路由、schema、响应字段、错误结构、鉴权 |
| Docs | 架构分册、API 契约、后端规范、changelog |

## 不需要同步的情况

如果改动只涉及错别字、注释或不影响架构事实的排版，可以不更新 changelog，但交付说明中应说明“不涉及架构事实变更”。

## 禁止项

- 不创建独立的 `docs/agent-monitoring.md`。
- 不把长篇架构规则复制到 `AGENTS.md`。
- 不在 API 契约中提前虚构尚未存在的 HTTP 接口。
- 不在前端规范中提前创建不存在的前端约定。

