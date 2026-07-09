# 03. Prompt 与上下文工程

## 范围

本文定义 PromptManager、ContextManager、prompt 模板结构、版本治理、trace 和评测规则。

## 核心原则

- Prompt 不是一段文案，而是受工程治理的模型输入协议。
- Prompt 不允许硬编码在 Agent 类里。
- Prompt 模板由 `PromptManager` 管理。
- 上下文分段、排序、裁剪由 `ContextManager` 管理。
- Prompt 改动必须可评测、可回滚。

## Prompt 固定分区

```text
[Role / Task]
[Rules]
[Input Schema]
[Context]
[RAG Evidence / Tool Results]
[Output Schema]
[Failure Policy]
```

## Prompt 元信息

每个 prompt 必须包含：

```yaml
id: domain_consultation.work_injury_recognition
version: v1
agent: DomainConsultationAgent
task_type: work_injury_recognition
model_profile: domain_reasoning
output_schema: AgentMessage
failure_policy:
  missing_evidence: cannot_answer
  missing_required_slot: ask_clarification
  tool_failed: return_error_reason
change_note: MVP 初始版本
```

## ContextManager 分段

| Section | 内容 | 裁剪策略 |
|---|---|---|
| `system_prefix` | Agent 身份、输出协议、安全边界、工具说明 | 最后裁剪 |
| `active_slots` | 当前会话已确认的业务槽位 | 尽量保留 |
| `rag_evidence` | 法规、地方政策、办事指南 | 尽量保留，可摘要 |
| `recent_turns` | 最近几轮对话摘要 | 可压缩 |
| `working_memory` | 上轮结论、待追问字段、工具失败摘要 | 可压缩 |
| `current_query` | 用户当前问题 | 不裁剪 |

## Prompt 模式取舍

MVP 使用：

- 抽取型模板。
- 证据问答模板。
- 工具调用模板。
- 评审 / 打分模板。
- 安全守卫模板。

MVP 不使用：

- 大量显式 Chain-of-thought。
- 每个 Agent 都做复杂 Critique-Revise。
- 大量 few-shot。
- 把业务硬规则全部塞进 prompt。

## Prompt 版本与回滚

Prompt 迭代流程：

```text
发现 badcase
  ↓
定位 prompt / context / tool / rule 问题
  ↓
修改 prompt 并升级版本
  ↓
运行固定 eval_cases
  ↓
指标通过则启用
  ↓
指标下降则回滚
```

## Prompt Trace

每次模型调用必须记录：

- `prompt_id`
- `prompt_version`
- `model_profile`
- `input_sections`
- `trimmed_sections`
- `output_schema_valid`
- token / 字符统计

