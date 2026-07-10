# 05. 数据、观测与评测

## 范围

本文定义项目自己的运行证据、用量、badcase 和 eval 契约。框架日志和 LangSmith 可以补充诊断，但不能成为唯一事实源。

## 当前实现与目标对象

| 对象 | 状态 | 回答的问题 |
|---|---|---|
| `SessionState` | 当前已实现 | 连续对话记住了哪些槽位和轮次 |
| `TaskState` | 当前已实现 | Native run 最终审计快照是什么 |
| `TraceEvent` | 当前已实现 | 中间发生了什么 |
| `RunReport` | 当前已实现 | 最终结果和基础指标是什么 |
| `BadcaseRecord` | 当前已实现 | 哪些运行需要回归 |
| `CaseRecord` | 目标 | 当前案件有哪些可信事实 |
| `RunSnapshot` | 目标 | 这次运行当前到哪里 |
| `CheckpointEnvelope` | 条件目标 | 运行时如何恢复 |
| `UsageRecord` | 目标 | 消耗了哪些模型、token 和能力资源 |
| `EvaluationArtifact` | 目标增强 | 如何复现完整评测上下文 |

这些对象使用不同生命周期，不得用 trace 直接恢复，也不得用 checkpoint 替代审计。

## 标识和版本

目标运行对象至少包含：

```text
schema_version
request_id
run_id
session_id
case_id
message_id
correlation_id
created_at
producer
```

当前已在 `ananhu_agent/workflow/contracts.py` 为 `RunRequest`、`WorkflowState` 和 `WorkflowResult` 增加 `schema_version`、`run_id`、`request_id`、`session_id`、`case_id` 和 `message_id`。`TraceEvent` 已包含可选 `runtime_name`、`runtime_version`、`node_id`、`attempt` 和 `logical_call_id`；当前 Runtime 与 Capability 链路按项目 trace schema 写入这些字段。后续 usage、Prompt、模型、知识语料和公式版本必须继续与同一运行证据关联。

## TraceEvent

当前事件覆盖请求、意图、工具、校验、安全和响应主链路。目标事件至少覆盖：

```text
request_received
state_transitioned
intent_recognized
facts_merged
clarification_requested
jurisdiction_resolved
context_built
model_started / model_finished / model_failed
capability_started / capability_finished / capability_failed
evidence_validated
answer_validated
safety_checked
checkpoint_saved / checkpoint_restored
response_ready
run_failed
```

业务事件 schema 由项目维护。LangGraph/LangSmith 事件通过 mapper 关联到项目事件，不能直接进入 Eval 契约。

每条 trace 可携带：

- `runtime_name`、`runtime_version`：区分 Native、LangGraph 等运行时实现和协议版本。
- `node_id`：产生事件的业务节点或阶段服务。
- `logical_call_id`：同一次逻辑调用的稳定 ID，重试时不变化。
- `attempt`：物理尝试次数，用于区分重试。

## 隐私与脱敏

- trace、session 和 badcase 默认不保存不必要的完整查询和敏感材料原文。
- 保存结构化摘要、hash、Evidence ID 和经过脱敏的最小诊断字段。
- 每类数据定义访问范围、保留期限和删除策略。
- 模型输入输出和附件处理记录 consent scope 与脱敏结果。

## UsageRecord

至少记录：

- provider、model、model profile。
- input/output/cache token 和估算费用。
- Prompt 版本和上下文 section token。
- capability 名称、版本、次数和耗时。
- run、node、tenant 和业务标签。

计费账本由项目维护，不依赖单一模型 SDK 或 LangSmith 聚合口径。

## BadcaseRecord

失败分类至少包含：

```text
routing_error
fact_extraction_error
fact_conflict_missed
jurisdiction_error
retrieval_miss
stale_or_invalid_evidence
citation_error
calculation_error
capability_error
response_inconsistency
safety_violation
runtime_or_recovery_error
```

Badcase 保存最小必要输入、关键状态版本、实际/期望结果、失败阶段、修复说明和是否进入 eval。

## Eval 分层

| 机制 | 主要指标 |
|---|---|
| 路由 | intent、复合需求、流程选择准确率 |
| 案件事实 | 抽取、确认、冲突发现、过期复用率 |
| RAG | 地区/时效过滤、Recall、MRR/NDCG、引用支持率 |
| 测算 | 输入准确、公式版本、结果误差、缺失输入处理 |
| 答复 | 事实一致性、不确定性披露、安全违规率 |
| Context | token、关键证据保留率、裁剪原因 |
| Runtime | phase、StopReason、重试、幂等、恢复成功率 |
| 成本性能 | token、费用、P50/P95 延迟、能力调用数 |

不得使用一个总体通过率证明所有机制有效。法规和测算优先使用确定性 verifier 或专家标注；LLM-as-Judge 仅作为辅助信号。

## 可复现性

每个 EvaluationArtifact 记录代码 commit、branch、数据集版本、fixture snapshot、模型配置、Prompt/Tool/语料版本、runtime 版本和每条 case 结果。Fake 与真实模型结果分开报告。

Native 和 LangGraph Runtime 运行同一 contract/eval 集时，比较业务结果、关键状态、能力调用和项目 trace 语义，不要求框架内部事件逐字一致。
