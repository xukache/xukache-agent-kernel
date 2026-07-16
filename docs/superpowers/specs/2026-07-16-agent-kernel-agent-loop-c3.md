# Agent Kernel C3 最小 Agent 推理循环设计

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | C3：实现最小 Agent 推理循环 |
| 日期 | 2026-07-16 |
| 状态 | 已完成 |
| 任务分支 | `task/c3-agent-loop` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.26` |
| 前置任务 | C1、C2、B3 已完成 |

本记录保存 C3 已由用户确认的最小执行边界。完整当前规格仍以
[`DEV_SPEC.md`](../../../DEV_SPEC.md) 为事实源；本记录不提前定义 C4 的多轮上限、
D 阶段 Tool 闭环、E 阶段 Memory 或 F 阶段 Runtime。

## 2. 确认的接口

使用异步函数：

```python
async def run_agent(
    definition: AgentDefinition,
    agent_input: AgentInput,
) -> AgentResult:
    ...
```

执行顺序固定为：

```text
AgentInput
  -> build_model_request
  -> await Model.generate
  -> ModelResponse
  -> AgentResult
```

C3 每次调用只执行一次 Model，不实现多轮循环。

## 3. 成功结果映射

```text
structured_output 或 text -> AgentResult.output
tool_calls                -> AgentResult.tool_calls
usage                     -> AgentResult.usage
model_id                  -> AgentResult.model_id
```

优先使用 `structured_output`；没有结构化输出时使用 `text`。

成功结果固定为：

```text
status      = succeeded
stop_reason = completed
error       = None
```

## 4. 错误结果映射

`ModelError` 转换为 `ErrorInfo`，保留 Model 的稳定错误码、来源、可重试性和脱敏
details，不暴露 Provider Exception。

普通 Model 错误：

```text
status      = failed
stop_reason = error
```

`model.cancelled` 和 `asyncio.CancelledError`：

```text
status      = cancelled
stop_reason = cancelled
```

没有可用 Model usage 时使用空 `Usage()`，不伪造 Token 数量。

未预期的运行时异常转换为：

```text
code        = agent.internal
source      = agent
status      = failed
stop_reason = error
```

不把原始异常文本写入公开 `ErrorInfo.message`。

## 5. Tool Call 边界

C3 不执行 Tool。若 Model 返回 Tool Call 且没有可作为最终结果的输出，转换为
`agent.internal` 失败结果，并保留 `tool_calls` 作为证据。Tool 闭环由后续任务负责。

## 6. 非职责

- 不处理 `max_model_rounds`。
- 不执行多轮 Model 调用。
- 不执行 Tool 或组装 Tool Schema。
- 不读取或写入 Memory。
- 不创建 RunContext、run_id、deadline 或事件。
- 不实现 Streaming、Retry 或 Runtime 生命周期。

## 7. 文件与测试

| 文件 | 职责 |
|---|---|
| `src/agent_kernel/agent/engine.py` | C3 最小 Agent 执行函数 |
| `src/agent_kernel/agent/__init__.py` | 公开导出 `run_agent` |
| `tests/unit/agent/test_agent_engine.py` | 成功、错误、取消和 Tool Call 边界 |

C3 只关联 K-001、K-007，不运行 RD-002；RD-002 由 C5 使用真实 Provider 验收。
