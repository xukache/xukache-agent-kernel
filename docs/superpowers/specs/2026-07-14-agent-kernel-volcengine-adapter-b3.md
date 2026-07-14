# Agent Kernel B3 Volcengine Ark Model Adapter 记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | B3：实现首个真实 Model Provider Adapter |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/b3-real-model-provider-adapter` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | B1、B2 已完成 |

本记录实现第一个真实 Provider Adapter 的配置、HTTP 调用和响应归一化，
不实现 Agent、Tool 执行、Runtime、结构化输出最终解析或 Streaming 增量转换。

## 2. Provider 配置

首个 Provider 由当前项目的 YAML Model Catalog 配置为 Volcengine Ark：

```text
ANANHU_MODEL_CATALOG
VOLCENGINE_API_KEY
ANANHU_REAL_MODEL_SMOKE
```

默认 Catalog 为 `config/models.yaml`，其结构为：

```yaml
version: 1
default:
  provider: volcengine
  model: doubao-seed-2-0-mini-260428
providers:
  volcengine:
    adapter: volcengine_ark
    api_key_env: VOLCENGINE_API_KEY
    base_url: https://ark.cn-beijing.volces.com/api/v3
    timeout_seconds: 30
    models:
      doubao-seed-2-0-mini-260428:
        capabilities: [generate]
```

`VolcengineArkConfig.from_environment()` 只在 Adapter 层读取环境变量定位
Catalog 和读取密钥；`from_yaml()` 负责解析具体配置：

- 缺少 `VOLCENGINE_API_KEY` 时立即抛出配置错误。
- 缺少 Provider、模型、Endpoint 或非法超时时间时立即抛出配置错误。
- `ANANHU_MODEL_CATALOG` 可切换整套 Provider 配置，便于官方迁移、代理或兼容网关调整。
- API Key 在 dataclass repr 中隐藏。
- 模型标识属于运行配置，不进入 Kernel Schema 或架构常量。

本地密钥不写入仓库、测试输出、Result、Event 或普通日志。

## 3. Adapter 边界

```text
VolcengineArkConfig
  -> VolcengineArkModel
      -> ModelRequest
      -> HTTP Chat Completions
      -> ModelResponse
```

Adapter 只依赖 `agent_kernel.model.Model`、Model Schema、ModelError 和
`httpx`。Provider 请求体、Authorization Header、HTTP 状态码和原始响应
都被限制在 Adapter 内。

请求转换包括：

- instructions、context、Memory 投影和 input 转成 messages。
- ToolSchema 转成 Provider 可见的 function schema。
- output_schema 转成受控 response format。

响应转换包括：

- text / structured output。
- tool_calls 和 JSON arguments。
- prompt、completion、total token usage。
- stop、tool_call、length、content_filter finish reason。
- 仅白名单提取 response id 为 `provider_metadata.request_id`。

## 4. 错误映射

| Adapter 情况 | Kernel 错误 |
|---|---|
| 缺少配置 | `ValueError`，运行前失败 |
| HTTP 429 | `ModelError(model.rate_limit, retryable=True)` |
| HTTP 400 / 422 | `ModelError(model.format)` |
| HTTP 其他错误 | `ModelError(model.provider)` |
| HTTP / Client Timeout | `ModelError(model.timeout, retryable=True)` |
| 请求网络异常 | `ModelError(model.provider, retryable=True)` |
| 响应结构不符合协议 | `ModelError(model.format)` |

错误消息不复制 Provider 原始响应，不暴露凭证。真正的重试由后续
Runtime / Execution 治理，Adapter 不自行重试。

## 5. 能力声明

当前 B3 明确声明：

```text
capabilities = {"generate"}
```

`stream()` 不返回伪造数据，而是显式抛出能力未启用的 `ModelError`。
B5 负责真实 Provider Streaming 增量转换，完成后再扩展能力声明。

## 6. 测试和验证

| 命令 | 结果 |
|---|---|
| `uv run pytest -q` | 通过，26 passed |
| `uv run pytest -q tests/integration/model tests/architecture` | 通过，10 passed |
| `uv lock --check` | 通过 |
| `uv build` | 通过，Wheel 包含 `adapters/model/volcengine.py` |
| `git diff --check` | 通过 |

集成测试使用 `httpx.MockTransport`，只验证请求转换和错误映射，不把 Mock
结果记录为真实对话证据。

当前 `ANANHU_REAL_MODEL_SMOKE=0`，尚未执行真实网络请求，因此真实
Provider Smoke 状态为 `NOT RUN`；这不影响 B3 的确定性 Adapter 实现已完成，
也不能将其视为 RD-001 真实对话验收通过。

## 7. 后续边界

- B4 负责结构化输出请求、解析和格式错误转换。
- B5 负责真实 Streaming 增量转换、合并和最终响应一致性。
- B6 使用 A5 证据基座执行 RD-001。
- Runtime / Execution 后续负责取消传播、Retry 和幂等治理。
