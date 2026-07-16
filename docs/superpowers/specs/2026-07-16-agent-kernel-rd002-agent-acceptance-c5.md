# Agent Kernel C5 RD-002 Agent 真实验收设计

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | C5：完成 RD-002 Agent 真实任务验收 |
| 日期 | 2026-07-16 |
| 状态 | 已完成 |
| 任务分支 | `task/c5-rd002-agent-acceptance` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.26` |
| 前置任务 | C1、C2、C3、C4、B6、A5 已完成 |

本记录保存 C5 已由用户确认的真实验收边界。完整当前规格仍以
[`DEV_SPEC.md`](../../../DEV_SPEC.md) 为事实源。

## 2. 固定真实场景

```text
RD-002
原始输入：请完成任务：计算 9 + 6，并返回结构化结果。
输出 Schema：result 为 integer，禁止额外字段
```

真实链路：

```text
真实 Volcengine Model
  -> AgentDefinition
  -> AgentInput
  -> run_agent
  -> AgentResult
```

## 3. 精确断言

真实 Provider 成功时必须满足：

```text
AgentResult.status == succeeded
AgentResult.output.result == 15
AgentResult.stop_reason == completed
AgentResult.model_id 非空
AgentResult.usage 字段存在
ModelRequest.instructions / input / output_schema 可追溯
```

证据至少保存：

```text
test_id、run_id、scope、model_id、provider
原始输入、预期结构化断言、ModelRequest 摘要
AgentResult 摘要、usage、stop_reason、latency、status
```

## 4. 状态规则

- `ANANHU_REAL_MODEL_SMOKE` 未设置为 `1`：记录 `NOT RUN`。
- 真实 Provider、凭证或网络不可用：记录 `BLOCKED`。
- Provider 返回行为不符合断言：记录 `FAIL` 并让测试失败。
- 真实链路和全部断言通过：记录 `PASS`。
- RD-002 必须与 RD-001 一起运行，形成阶段 C 的累计回归。

## 5. 非职责

- 不修改 Agent Engine 的执行语义。
- 不使用 Stub Model、固定 Model 输出或 fallback 伪造真实结果。
- 不实现 Tool、Memory、Runtime 或 RD-003 及后续场景。
