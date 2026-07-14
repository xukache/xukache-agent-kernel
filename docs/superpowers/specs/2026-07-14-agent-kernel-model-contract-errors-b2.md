# Agent Kernel B2 Model Contract 与错误语义记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | B2：定义 Model Contract 与错误语义 |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/b2-model-contract-errors` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | B1 已完成 |

本记录只确认 Model 的可替换行为契约和错误分类，不实现 Provider Adapter、
真实调用、RunContext 或 Runtime 重试。

## 2. 学习目标

B2 回答：

> 如何让不同 Provider 遵守同一调用行为？

统一调用边界：

```text
Model.generate(request)
  -> Awaitable[ModelResponse]

Model.stream(request)
  -> AsyncIterator[ModelStreamChunk]
```

Model 只负责生成和增量输出。它不负责 Tool 执行、Memory 读写、Workflow
路由、Runtime 生命周期或重试决策。

## 3. Model Protocol

`agent_kernel.model.Model` 使用 `typing.Protocol` 和 `@runtime_checkable`：

```python
class Model(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]: ...
```

- `generate` 返回一次完整 `ModelResponse`。
- `stream` 返回只能消费一次的有序异步增量流。
- Protocol 不包含 Provider SDK、凭证、HTTP 客户端或具体实现状态。
- 当前不把 `RunContext` 或取消令牌加入签名；F1 / Runtime 任务确认执行上下文后再接入。

## 4. Streaming 增量

`ModelStreamChunk` 支持以下 Provider Neutral 负载：

| 字段 | 语义 |
|---|---|
| `text_delta` | 文本增量 |
| `structured_delta` | 结构化输出增量 |
| `tool_call_delta` | Tool Call 的部分调用意图 |
| `usage` | Provider 在流中返回的归一化 usage |
| `finish_reason` | 流结束原因 |
| `model_id` | 实际模型标识 |

`ToolCallDelta` 允许只携带 call_id、name 或部分参数文本中的一个，
因为 Provider 可能分多个 chunk 发送调用信息。F3 / B5 再确认完整增量
合并和最终响应一致性。

## 5. Model 错误语义

`ModelErrorCode` 使用 Provider Neutral 稳定值：

| 错误码 | 语义 | 常见 retryable 属性 |
|---|---|---|
| `model.provider` | Provider 调用或响应不可用 | 否 |
| `model.timeout` | 调用超过时限 | 可为 true |
| `model.rate_limit` | Provider 限流 | 可为 true |
| `model.format` | 请求或响应格式错误 | 否 |
| `model.cancelled` | 调用被取消 | 否 |

`ModelError` 继承公共 `KernelError`，并包含：

```text
code
message
retryable
details
```

`retryable=True` 只是错误属性，不会自行触发重试。Runtime / Execution
必须在后续任务中结合幂等性、策略、次数、deadline 和取消状态决定是否重试。
Provider SDK Exception 必须由 Adapter 转换为 `ModelError`，并保留异常链，
不能将 SDK 类型传入 Kernel 公共协议。

## 6. 共享 Contract Test

`tests/contract/model/test_model_contract.py` 固定以下合同：

1. 实现具备 `generate` 和 `stream` 行为即可符合 `Model` Protocol。
2. `generate` 必须返回 `ModelResponse`。
3. `stream` 必须返回可按顺序消费的 `ModelStreamChunk`。
4. 完整流必须提供明确结束原因或终态信息。
5. Provider、超时、限流、格式和取消错误必须映射到 `ModelError`。
6. 错误必须保留 Provider Neutral code 和 retryable 属性。

测试替身只验证合同和错误传播，不作为真实 Model 完成证据。

## 7. 验证结果

| 命令 | 结果 |
|---|---|
| `uv run pytest -q tests/contract/model/test_model_contract.py` | 通过，4 passed |
| `uv run pytest -q` | 通过，18 passed |
| `uv run pytest -q tests/architecture` | 通过，2 passed |
| `uv lock --check` | 通过 |
| `uv build` | 通过，成功构建 sdist 和 wheel |
| `git diff --check` | 通过 |

B2 没有执行真实 Provider；B3 才开始 Provider Adapter 接入，RD-001 仍由
B3/B4/B6 完成。

## 8. 与后续任务的边界

- B3 将 Provider SDK 请求和响应转换为 B1/B2 公共协议。
- B4 负责结构化输出解析和格式错误映射。
- B5 负责真实 Provider Streaming 增量转换和合并。
- F4 / F7 负责取消传播、Retry 和幂等治理。
