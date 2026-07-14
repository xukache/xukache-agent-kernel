# Agent Kernel B1 ModelRequest 与 ModelResponse 契约记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | B1：定义 ModelRequest 与 ModelResponse |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/b1-model-request-response` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | A2、A4、A5 已完成 |

本记录只确认 Model 的 Provider Neutral 数据协议，不实现 Model Protocol、
Provider Adapter、真实调用、结构化输出转换或 Streaming。

## 2. 学习目标

B1 回答：

> Agent 和 Provider 之间真正需要交换哪些数据？

关键边界是：

```text
Agent 组装 ModelRequest
  -> Model Adapter 转换 Provider 请求
  -> Provider 返回原始响应
  -> Model Adapter 转换 ModelResponse
  -> Agent 处理文本、结构化结果或 Tool Call
```

Provider SDK、凭证、网络客户端和可执行 Tool 都不进入这些 Schema。

## 3. 已确认类型

公开入口：

```python
from agent_kernel.model import (
    FinishReason,
    MessageRole,
    ModelMemoryItem,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCall,
    ToolSchema,
    Usage,
)
```

### 3.1 ModelRequest

`ModelRequest` 是 Agent 交给 Model Adapter 的一次请求，包含：

| 字段 | 语义 |
|---|---|
| `instructions` | 可选系统级指令文本；Prompt 所有权仍属于 Agent |
| `input` | 本次用户或上游模块输入，支持文本或结构化 JSON 对象 |
| `context` | 已排序的 Provider Neutral 消息上下文 |
| `memory_items` | Memory 进入 Model 请求的只读投影 |
| `tool_schemas` | Model 可见的工具描述，不包含可执行对象 |
| `output_schema` | 可选结构化输出 JSON Schema |
| `runtime_metadata` | 受控、可脱敏的运行元数据 |

`ModelRequest` 不携带 Model 实例、Tool callable、Provider SDK 类型、
凭证、run 状态或完整事件日志。

### 3.2 ModelResponse

`ModelResponse` 是 Model Adapter 返回给 Agent 的一次归一化响应，包含：

| 字段 | 语义 |
|---|---|
| `text` | 可选自然语言输出 |
| `structured_output` | 可选结构化 JSON 对象 |
| `tool_calls` | Model 生成的结构化调用意图 |
| `usage` | `input_tokens`、`output_tokens`、`total_tokens` |
| `finish_reason` | `stop`、`tool_call`、`length`、`content_filter` 或 `cancelled` |
| `model_id` | 实际使用的模型标识 |
| `provider_metadata` | 受控的 Provider 扩展元数据，不保存原始响应 |

至少必须存在 `text`、`structured_output` 或 `tool_calls` 之一。
`tool_call` 结束原因必须包含 Tool Call；`stop` 结束原因不能包含 Tool Call。

## 4. 类型与序列化规则

- 所有 B1 Schema 使用 `frozen=True`、`extra="forbid"`、`strict=True`。
- 集合使用 tuple，防止调用方通过 list 原地修改请求或响应语义。
- 开放 JSON 只出现在实际开放的 Schema、metadata 和结构化输出位置。
- 所有字段均可通过 Pydantic JSON 模式和 JSON 文本序列化。
- `ToolCall` 只保存 `call_id`、名称和结构化参数，绝不保存 Python callable。
- `ToolSchema` 只描述 Model 可见的名称、说明和输入 Schema。
- `ModelMemoryItem` 是 Model 请求侧的只读投影，不取代 E 阶段的 `MemoryItem`。

## 5. 验证结果

| 命令 | 结果 |
|---|---|
| `uv run pytest -q tests/unit/model/test_model_schemas.py` | 通过，4 passed |
| `uv run pytest -q` | 通过，14 passed |
| `uv run pytest -q tests/architecture` | 通过，2 passed |
| `uv lock --check` | 通过 |
| `uv build` | 通过，成功构建 sdist 和 wheel |
| `git diff --check` | 通过 |

B1 没有执行真实 Provider；RD-001 仍由 B3/B4/B6 完成。

## 6. 与后续任务的边界

- B2 定义 `Model` Protocol、`generate / stream` 能力和错误语义。
- B3 在 Adapter 层接入真实 Provider，负责 SDK 转换和能力预检。
- B4 负责结构化输出转换与格式错误。
- B5 负责 Streaming 增量转换。
- C2 负责 Agent 将 Definition、Memory 和 Tool Schema 组装成 ModelRequest。

## 7. 当前限制

- 尚未定义 Model Protocol 和异步调用方法。
- 尚未冻结 Provider 配置、凭证环境变量和具体 SDK。
- `ModelMemoryItem` 只是请求侧投影，Memory Core 的完整 MemoryItem 由 E1 确认。
