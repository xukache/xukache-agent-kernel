# 04. 工具与模型治理

## 范围

本文定义 ToolRegistry、ToolExecutor、ToolCallRequest、ToolCallResult、ModelRouter 和多模型策略。

## Tool 清单

MVP 工具：

| Tool | 职责 |
|---|---|
| `PolicyRAGTool` | 检索法规、地方政策、办事指南 |
| `PaymentCalculationTool` | 工伤待遇测算 |
| `RegionPolicyFilterTool` | 根据省市过滤政策 |
| `CitationFormatterTool` | 格式化引用依据 |
| `TraceTool` | 写入调用链 trace |
| `BadcaseTool` | 记录失败案例 |

不进入 MVP：

- `HazardImageTool`
- `SpeechRecognitionTool`
- `WebSearchTool`

当前已落地的本地 MVP 工具函数：

| 函数 | 对应 Tool | 职责 |
|---|---|---|
| `search_policy` | `PolicyRAGTool` | 基于 `data/policies/policy_fixtures.jsonl` 做确定性关键词检索，并返回 `documents` 与 `citation`。 |
| `calculate_payment` | `PaymentCalculationTool` | 按伤残等级月数和本人工资计算一次性伤残补助金，返回分项、公式、假设和免责声明。 |
| `format_citations` | `CitationFormatterTool` | 将工具返回的 citation 按稳定顺序格式化为最终答案引用标签。 |

## ToolRegistry

每个工具必须注册：

```yaml
name: PolicyRAGTool
description: 检索工伤法规、地方政策、办事指南
risk_level: read_only
timeout_ms: 3000
allowed_callers:
  - PolicyRAGAgent
  - DomainConsultationAgent
input_schema:
  query: string
  province: string
  city: string
  top_k: integer
output_schema:
  documents: array
  citations: array
```

当前 MVP 代码基线已落地 `ToolDefinition` 和 `ToolRegistry`：

- `name`、`description`、`risk_level`、`timeout_ms`、`allowed_callers` 作为工具元数据保存。
- `required_input_keys` 作为 MVP 阶段的最小输入校验边界。
- `handler` 只允许由 `ToolExecutor` 调用，Agent 不直接调用底层工具函数。

## ToolExecutor

Agent 只能产生 `ToolCallRequest`，所有工具必须经过 `ToolExecutor`。

`ToolExecutor` 负责：

- 工具注册校验。
- Agent 调用权限校验。
- 参数 schema 校验。
- 风险等级检查。
- 超时控制。
- 重复调用拦截。
- 错误码归一。
- fallback 标记。
- trace 写入。

当前 MVP 代码基线已落地：

- 未注册工具返回 `tool_not_registered`。
- 调用方不在 `allowed_callers` 时返回 `caller_not_allowed`。
- 缺少 `required_input_keys` 时返回 `invalid_input_schema`。
- handler 异常统一返回 `tool_handler_error`，不向最终用户泄露原始异常。
- 成功调用写入 `tool_finished` trace，失败调用写入 `tool_failed` trace。

以下治理项需在真实 RAG / 真实模型接入前补齐，不得长期依赖最小实现：

- 基于结构化 input / output schema 的类型校验。
- 超时控制和取消策略。
- 风险等级策略执行。
- 重复调用拦截。

## ToolCallResult

工具返回必须结构化：

```json
{
  "tool_call_id": "tool_001",
  "tool_name": "PolicyRAGTool",
  "called_by": "PolicyRAGAgent",
  "tool_status": "success",
  "tool_error_code": null,
  "latency_ms": 320,
  "input": {},
  "output": {},
  "fallback_used": false
}
```

## ModelRouter

模型配置按能力分层：

| model_profile | 用途 |
|---|---|
| `intent_fast` | 意图识别、槽位抽取 |
| `domain_reasoning` | 政策咨询、复杂法规推理 |
| `verifier` | 答案校验、冲突检查 |
| `judge` | 离线评测 |

多模态模型不进入 MVP。

## 模型选择原则

- 简单分类用轻量模型。
- 法规推理用强推理模型。
- 结构化计算由工具完成，模型只解释。
- 低置信度优先追问，不盲目升级复杂链路。
- 模型调用必须记录 prompt、usage、latency 和错误信息。
