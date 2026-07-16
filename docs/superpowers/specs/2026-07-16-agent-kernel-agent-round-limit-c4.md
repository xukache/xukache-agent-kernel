# Agent Kernel C4 运行上限与停止原因设计

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | C4：实现运行上限与停止原因 |
| 日期 | 2026-07-16 |
| 状态 | 已完成 |
| 任务分支 | `task/c4-agent-round-limit` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.26` |
| 前置任务 | C3 已完成 |

本记录保存 C4 已由用户确认的最小实现边界。完整当前规格仍以
[`DEV_SPEC.md`](../../../DEV_SPEC.md) 为事实源；本记录不提前定义 D 阶段 Tool
执行和完整多轮闭环。

## 2. 轮次定义

每次 `await Model.generate(request)` 计为一轮 Model Round。

`AgentDefinition.max_model_rounds` 是一次 Agent 调用的硬上限。

## 3. 停止规则

```text
最终文本 / 结构化输出 -> succeeded / completed
Model 错误             -> failed / error
Model 取消             -> cancelled / cancelled
达到上限               -> failed / max_model_rounds
```

达到上限时使用：

```text
error.code      = agent.limit
error.source    = agent
error.retryable = false
error.details    = {
    "max_model_rounds": N,
    "rounds": N,
}
```

已产生的 `usage`、`model_id` 和 `tool_calls` 保留，不伪造 Token 数量。

## 4. 当前 Tool Call 边界

C4 只负责判断是否还能继续下一轮，不执行 Tool。

在当前没有 Tool 执行器的阶段：

- `max_model_rounds=1` 且 Model 返回 Tool Call 时，返回 `agent.limit`。
- 尚未达到上限但没有 Tool 执行器时，返回 `agent.internal`。
- D 阶段接入 Tool 后，Tool Result 才能驱动下一轮 Model 调用，并复用本规则。

## 5. 非职责

- 不新增 `run_agent` 公共接口。
- 不执行 Tool。
- 不读取或写入 Memory。
- 不创建 Runtime、RunContext 或事件。
- 不运行 RD-002。

## 6. 验收

C4 关联 K-001，必须区分正常完成、Model 错误、取消和达到运行上限。
