# Agent Kernel B5 Provider Streaming 转换记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | B5：实现 Provider Streaming 转换 |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/b5-provider-streaming-conversion` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | B3、B4 已完成 |

本记录只确认 Provider SSE 增量到 `ModelStreamChunk` 的转换，不负责
Runtime 重试、取消治理或最终 `ModelResponse` 聚合。

## 2. Streaming 边界

```text
Model.stream(request)
  -> HTTP POST(stream=true)
  -> Provider SSE data events
  -> ModelStreamChunk
```

Adapter 支持：

- 文本增量 `delta.content` -> `text_delta`
- Tool Call 增量 -> `ToolCallDelta`
- Provider usage -> `Usage`
- Provider finish reason -> `FinishReason`
- `data: [DONE]` 传输结束标记

`stream()` 返回一次性消费的异步迭代器，Provider SDK 类型和 SSE 文本不
进入 Kernel。

## 3. 结构化输出流

`ModelStreamChunk.structured_delta` 当前要求 JSON 对象，不能表达半截 JSON
字符串。因此当请求包含 `output_schema` 时：

1. 缓存 Provider 的结构化 JSON 文本片段。
2. 收到合法 `finish_reason` 后复用 B4 的 JSON 解析和 Schema 校验。
3. 输出一个完整的 `structured_delta`。
4. 输出最终 `finish_reason` Chunk。

不自动修复、不 fallback、不执行重试。

## 4. 错误与结束语义

| 情况 | Kernel 结果 |
|---|---|
| HTTP 429 | `ModelError(model.rate_limit, retryable=True)` |
| HTTP 400 / 422 | `ModelError(model.format)` |
| HTTP 其他错误 | `ModelError(model.provider)` |
| HTTP / Client Timeout | `ModelError(model.timeout, retryable=True)` |
| SSE JSON 或字段格式错误 | `ModelError(model.format)` |
| `[DONE]` 前无合法 `finish_reason` | `ModelError(model.format)` |

Adapter 不把 `[DONE]` 当作业务结束原因，也不伪造默认 `stop`。

## 5. 能力声明

当前能力：

```text
{"generate", "stream"}
```

这只表示 Adapter 能提供完整调用和增量调用，不表示 Runtime 已经具备
取消、重试、事件持久化或最终结果聚合能力。

## 6. 测试和验证

| 验证 | 结果 |
|---|---|
| Streaming 集成测试 | 已通过，5 passed |
| 全量测试 | 已通过，33 passed |
| Adapter + Architecture 测试 | 已通过，17 passed |
| `uv lock --check` | 已通过 |
| `uv build` | 已通过 |
| `git diff --check` | 已通过 |

测试使用 `httpx.MockTransport` 和确定性 SSE 内容，只证明 Adapter 转换
行为，不作为真实 Provider Smoke 或 RD-008 通过证据。

## 7. 后续边界

- B6 负责真实 Provider 下的 RD-001 结构化验收。
- Runtime / Agent 后续负责把完整增量聚合为最终 `ModelResponse`，并治理
  取消、重试和运行事件。
