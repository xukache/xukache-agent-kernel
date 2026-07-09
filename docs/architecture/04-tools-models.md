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

