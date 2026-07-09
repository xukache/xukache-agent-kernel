# 05. 数据模型与观测诊断

## 范围

本文定义 MVP 阶段的运行证据、Trace、Report、Badcase、Eval 数据结构和观测规则。

## 三类运行证据

| 类型 | 作用 |
|---|---|
| `task_states` | 当前轮运行快照，回答“这轮跑到哪一步” |
| `agent_traces` | 逐事件时间线，回答“中间发生了什么” |
| `run_reports` | 运行摘要，回答“最后拿什么做统计” |

## task_states

核心字段：

- `id`
- `session_id`
- `turn_id`
- `user_query`
- `status`
- `current_phase`
- `raw_intent`
- `revised_intent`
- `active_slots`
- `missing_slots`
- `route_agents`
- `prompt_refs`
- `tool_steps`
- `model_attempts`
- `fallback_used`
- `error_message`

## agent_traces

每条 trace event 至少包含：

- `id`
- `request_id`
- `session_id`
- `event_type`
- `phase`
- `payload`
- `latency_ms`
- `created_at`

关键事件类型：

- `request_received`
- `intent_recognized`
- `intent_revised`
- `slots_merged`
- `prompt_built`
- `model_called`
- `tool_called`
- `tool_finished`
- `tool_failed`
- `answer_validated`
- `safety_checked`
- `response_ready`
- `request_failed`

## run_reports

运行摘要字段：

- `id`
- `session_id`
- `final_status`
- `final_intent`
- `route_agents`
- `tool_count`
- `model_attempts`
- `prompt_refs`
- `prompt_metadata`
- `output_schema_valid_rate`
- `token_usage`
- `latency_ms`
- `fallback_used`
- `safety_result`
- `badcase_candidate`

## badcases

结构化字段：

- `id`
- `request_id`
- `session_id`
- `turn_id`
- `query`
- `predicted_intent`
- `issue_type`
- `agent_route`
- `tool_calls`
- `actual_answer`
- `expected_answer`
- `correction_note`
- `added_to_eval`
- `fixed`
- `created_at`

badcase 来源：

- 用户主动标记。
- 用户负反馈。
- 系统自动标记。
- eval 失败。

自动标记条件：

- 意图置信度低。
- RAG 无结果。
- 答案无引用依据。
- 地区政策不匹配。
- 工具调用失败。
- 输出 schema 不合法。
- 安全守卫拦截。

安全守卫 issue code：

- `absolute_commitment`
- `medical_grade_commitment`
- `agency_decision_substitution`
- `precise_amount_commitment`

## eval_cases

MVP 评测集至少覆盖：

- 工伤认定。
- 劳动能力鉴定。
- 待遇测算。
- 复合问题。
- 证据不足和安全边界问题。

## Eval 评测指标

`EvalRunner` 输出总通过率和分层指标，便于定位失败发生在意图、槽位、引用、工具、安全还是性能层：

- `total`、`passed`、`failed`：基于 `expect_contains` 的答案片段总分。
- `intent_accuracy`：仅统计声明 `expected_intent` 的 case。
- `slot_accuracy`：仅统计声明 `expected_slots` 的 case，按期望槽位是否全部进入 active slots 计分。
- `citation_accuracy`：仅统计声明 `expected_citations` 的 case，按 RAG 返回引用标题是否命中期望来源计分。
- `tool_success_rate`：统计实际发生工具调用的 case，要求本轮工具调用全部成功。
- `unsafe_expression_rate`：统计未通过安全守卫的 case 占比。
- `latency_ms_avg`：eval 单轮 `orchestrator.ask()` 平均耗时。

## Prompt 评测

Prompt 指标：

- `format_valid_rate`
- `missing_slot_accuracy`
- `citation_grounded_rate`
- `cannot_answer_correctness`
- `tool_call_correctness`
- `unsafe_expression_rate`
- `prompt_token_cost`
- `prompt_latency`
