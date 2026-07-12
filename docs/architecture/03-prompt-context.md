# 03. Prompt、上下文与记忆

## 范围

本文定义框架中立的 Prompt、上下文预算、案件事实和记忆治理。LangGraph node 不得自行拼接 Prompt 或直接读取完整聊天历史。

## 核心原则

- Prompt 是版本化模型输入协议，不是 Agent 类中的字符串。
- 上下文是当前业务状态的受控投影，不是所有历史的拼接。
- 记忆不是知识库，也不等于聊天记录。
- 已确认案件事实不能被模型摘要静默覆盖。
- 裁剪策略按证据等级和业务风险，而不是只按时间远近。

## Prompt 分层

| 层级 | 内容 | 变化频率 |
|---|---|---|
| 稳定段 | 职责、输出契约、安全规则、能力 schema | 低 |
| 半稳定段 | jurisdiction、请求类型、Prompt/Tool/语料版本 | 中 |
| 动态段 | 当前请求、案件事实、证据、能力结果、近期对话 | 高 |

缓存键至少包含 `prompt_version`、`capability_registry_version`、`policy_corpus_version`、`jurisdiction` 和 `model_profile`。模型供应商缓存只用于性能优化。

## Prompt 固定分区

```text
[Role / Task]
[Rules / Safety]
[Input Schema]
[Confirmed Case Facts]
[Candidate or Conflicting Facts]
[Evidence / Capability Results]
[Recent Relevant Conversation]
[Current Request]
[Output Schema]
[Failure Policy]
```

## 案件事实

每条 `CaseFact` 包含：

- `name`、`value` 和数据类型。
- `source`、`source_ref`。
- `confirmation_status` 和 `confidence`。
- `valid_from`、`valid_to`、`supersedes`。

模型抽取、材料 OCR 和工具结果使用不同来源类型。只有用户确认或可信系统规则可以把候选事实提升为已确认事实。

## 记忆分层

```text
Case facts             跨会话业务事实
Working memory         当前请求、待补充项、关键失败
Conversation summary   连续对话辅助信息
Evidence cache         带语料版本和有效期的检索结果
Calculation snapshot   带输入和公式版本的计算结果
```

政策语料版本、jurisdiction、事故日期、关键事实或计算公式变化时，依赖项必须失效。会话摘要不能作为政策依据或用户确认事实。

## ContextManager 预算

| 等级 | 内容 | 策略 |
|---|---|---|
| P0 | 当前请求、已确认关键事实、安全规则 | 不静默裁剪 |
| P1 | 直接支撑结论的政策证据、计算输入 | 高保留，必要时结构化压缩 |
| P2 | 待确认事实、近期相关对话 | 可摘要 |
| P3 | 低相关证据、重复解释、原始长输出 | 优先删除 |

工具长输出应在进入上下文前结构化和裁剪，避免在最终 Prompt 阶段才粗暴截断。

模型抽取的案件槽位必须使用项目约定的规范字段名。省级地区简称在进入可信案件事实前由
确定性槽位规则归一为行政区全称；模型不得自行扩展字段名或把可选字段列为当前意图的必填缺口。

每次构建输出 `ContextBuildReport`：

- 各 section 候选数、入选数和 token。
- 裁剪顺序和原因。
- 被淘汰 Evidence/Memory ID。
- Prompt、模型、语料和能力版本。

## Prompt 版本与回滚

```text
发现 badcase
  -> 定位事实 / context / retrieval / prompt / model / safety
  -> 修改对应机制并升级版本
  -> 运行机制专项 eval
  -> 运行全量回归
  -> 指标满足门槛后启用，否则回滚
```

Prompt 修改不能用单一 LLM-as-Judge 分数验收。法规引用、测算和安全问题优先使用确定性断言或专家标注。

## Trace 要求

每次模型调用记录：`prompt_id`、`prompt_version`、`model_profile`、输入 section、裁剪报告、关联 Evidence ID、schema 校验、token、延迟和错误。默认 trace 保存摘要、hash 和引用，不记录不必要的完整敏感原文。

## TUI 展示与 Reasoning 边界

Textual 运行检查器可展示 Prompt ID/version、profile、schema 摘要和裁剪脱敏后的 message 视图，但这些
展示数据只能来自 ContextManager/PromptManager 已构造完成的真实 `ModelRequest`，不得用 profile 配置或
LangGraph state 冒充模型输入。案件槽位只显示项目规范字段；省级地区继续在进入可信事实前归一化。

provider 显式返回的 `reasoning_content` 不属于 Prompt、上下文、记忆或业务事实。它只经模型适配器归一
化后进入序列化排除的瞬态 payload，按独立上限裁剪并执行与模型输出相同的敏感字段脱敏。Agent、
WorkflowState、TaskState、RunReport、SessionState、trace、badcase、eval 和 differential artifact 不得
保存、解析或依赖 reasoning 原文；新会话、清屏和退出时释放内存。该变化不改变 Prompt eval 口径，
但必须增加 reasoning 持久化零命中与 secret canary 测试。

## TUI 会话上下文查看

`F2` 或 `/context` 是展示层检查器，不是新的 Runtime memory 来源，也不改变
`WorkflowState`、`SessionState` 或 Prompt 输入。它显示两部分：

- 当前轮 `case_facts` 和阶段。
- 当前 `chat` 进程内已完成轮次的用户问题与可见回答摘要。

展示历史按 `turn_id` 去重，重试同一轮不会制造重复记录。`Ctrl+L` 只清屏，不清除当前
session 的展示历史；`Ctrl+N`、`/new` 和重启 `chat` 会创建新的 session。TUI 展示历史只存在
当前进程内，不替代 `SessionStateStore`、`TaskStateStore` 或业务 trace 的持久化职责。
