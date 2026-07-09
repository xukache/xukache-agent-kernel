# API 契约总纲

本文是安安虎工伤智能助手 Agno 多 Agent 重构版的 API 契约入口。

## 当前状态

当前 MVP 是无前端交互式 CLI 应用，不暴露 HTTP API，不提供 WebSocket，不直接接入政府小程序接口。

因此当前阶段：

- 暂无公开 HTTP API。
- 暂无 FastAPI 路由。
- 暂无 API 领域契约分册。
- 暂无前端 adapter / Raw 类型同步要求。

## 后续启用条件

进入 `v0.2-api` 或 FastAPI 服务化阶段时，必须先更新本文，并创建：

```text
docs/api-contracts/
  00-conventions.md
  01-chat-agent.md
  02-trace-badcase.md
  03-evaluation.md
  99-changelog.md
```

具体是否采用上述分册名称，以实际接口领域为准。

## 契约纪律

后续新增 API 时，必须在实现前定义：

- 路径和方法。
- 请求字段、类型、必填性、枚举值。
- 响应字段、错误结构和状态码。
- 鉴权、租户、地区或调用方边界。
- 与 CLI / Agent runtime / trace / eval 的关系。
- 契约变更记录。

当前没有后端 API，不要创建空的 API 领域分册。

