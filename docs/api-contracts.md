# API 契约总纲

本文只描述安安虎 Agent Harness 的外部接口状态和启用条件。Agent 内部协议属于技术架构，不属于公开 API 契约。

## 当前状态

- 当前交付入口是 Typer CLI。
- 当前没有 HTTP API、WebSocket、SSE、前端或小程序直连接口。
- 因为没有真实外部 API，当前不创建 `docs/api-contracts/` 领域分册。
- 当前 CLI 通过 `WorkflowRuntime` 端口调用默认 Native Runtime。CLI 只负责输入输出适配，`RunRequest` 和 `WorkflowResult` 不依赖 Typer。

这项限制只约束当前交付范围，不限制 Agent 内核未来支持异步流式输出、多模态输入或其他客户端。

## 内外协议边界

以下属于内部架构协议，由 `docs/architecture/` 维护：

- `RunRequest`、`WorkflowState`、`StatePatch`、`WorkflowResult`。
- Agent、Capability、Evidence、Trace、Usage 和 Checkpoint 协议。
- LangGraph state 投影和 runtime adapter。

只有对外稳定暴露后，才在 API 契约中定义 HTTP 路径、鉴权、请求响应和流式事件。

## 后续启用条件

引入 FastAPI、WebSocket、SSE 或其他网络接口前必须先完成：

1. 明确服务边界、调用方、鉴权、租户和 jurisdiction 来源。
2. 冻结框架中立的请求、响应和流式事件 schema。
3. 定义 message/session/case/run 的授权和关联规则。
4. 定义幂等键、超时、取消、重试、错误码和限流策略。
5. 定义 PII 脱敏、审计、保留期限和删除规则。
6. 更新本文并创建 `docs/api-contracts/00-conventions.md`、领域契约和 API changelog。

## 外部接口演进原则

- HTTP、CLI、语音或其他入口都调用同一 application use case。
- 外部协议不得直接暴露 LangGraph `Command`、message、checkpoint 或 channel 类型。
- 流式输出使用项目自己的事件 schema，由运行时事件映射产生。
- API session ID 不能直接作为数据库授权依据，必须绑定可信身份和租户上下文。

## 契约纪律

- 不提前虚构尚未存在的接口路径。
- 不把 CLI 参数误写成 HTTP 契约。
- 不把 LangGraph/LangSmith 内部事件当作公开流式协议。
- 新增或修改外部接口时，契约文档、schema、实现、测试和 changelog 必须在同一变更中更新。
