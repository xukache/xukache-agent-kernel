# Agent Kernel B4 结构化输出转换记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | B4：实现结构化输出转换 |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/b4-structured-output-conversion` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | B3 已完成 |

本记录只确认显式结构化输出请求的转换和校验，不改变普通文本、
Tool Call 或 Streaming 边界。

## 2. 设计边界

`ModelRequest.output_schema` 保持可选：

```text
无 output_schema
  -> 保持普通文本或 Provider 返回对象的既有行为

有 output_schema
  -> Provider response_format
  -> JSON 字符串 / JSON 对象解析
  -> JSON Schema 本地校验
  -> ModelResponse.structured_output
```

Model 层支持普通文本、结构化输出和 Tool Call 三种合法结果。
B4 只在调用方明确提供 `output_schema` 时强制结构化，不要求所有 Model
调用都返回结构化结果。

## 3. 转换规则

| Provider 内容 | 有 `output_schema` | 结果 |
|---|---|---|
| JSON object | 是 | 校验后写入 `structured_output` |
| JSON string | 是 | `json.loads` 后校验并写入 `structured_output` |
| 非法 JSON string | 是 | `ModelError(model.format)` |
| 非 object JSON | 是 | `ModelError(model.format)` |
| Schema 不匹配 | 是 | `ModelError(model.format)` |
| 普通 string | 否 | 保持 `text` |
| JSON object | 否 | 保持 `structured_output` |

不执行自动修复、重试、固定输出或模拟 fallback。

## 4. Schema 校验

- `output_schema` 是 Provider Neutral JSON Schema。
- Adapter 使用 `jsonschema` 在响应边界执行本地校验。
- Provider 已返回成功但本地校验失败时，仍映射为 `model.format`。
- Schema、Provider SDK 和校验库只存在于 Adapter 边界，不进入 `agent_kernel`。

## 5. 测试和验证

| 验证 | 结果 |
|---|---|
| B4 结构化输出集成测试 | 已通过，3 passed |
| 全量测试 | 已通过，29 passed |
| Adapter + Architecture 测试 | 已通过，13 passed |
| `uv lock --check` | 已通过 |
| `uv build` | 已通过 |
| `git diff --check` | 已通过 |

测试使用 `httpx.MockTransport`，只证明请求转换、JSON 解析和 Schema
错误映射，不作为真实 Provider 或 RD-001 通过证据。

## 6. 后续边界

- B5 负责 Provider Streaming 的结构化增量转换和最终结果合并。
- B6 负责使用真实 Provider 执行 RD-001。
- Agent 层后续决定具体任务是否必须提供 `output_schema`。
