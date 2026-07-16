# Agent Kernel C2 Instructions 与 ModelRequest 组装设计

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | C2：实现 Instructions 与 ModelRequest 组装 |
| 日期 | 2026-07-16 |
| 状态 | 已完成 |
| 任务分支 | `task/c2-instructions-model-request` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.26` |
| 前置任务 | C1、B1 已完成 |

本记录保存 C2 已由用户确认的最小实现边界。完整当前规格仍以
[`DEV_SPEC.md`](../../../DEV_SPEC.md) 为事实源；本记录不提前定义 C3 的推理循环、
C4 的轮次限制或 D-G 的 Tool、Memory、Runtime 行为。

## 2. 目标

C2 解决：

> AgentDefinition 中的 Instructions、AgentInput 中的用户输入和输出 Schema，
> 如何确定性地形成一次 Provider Neutral 的 ModelRequest？

## 3. 确认的接口

使用无状态纯函数：

```python
def build_model_request(
    definition: AgentDefinition,
    agent_input: AgentInput,
) -> ModelRequest:
    ...
```

函数只做数据转换，不调用 `definition.model`。

## 4. 字段所有权与映射

```text
definition.instructions     -> ModelRequest.instructions
agent_input.input           -> ModelRequest.input
agent_input.output_schema   -> ModelRequest.output_schema
```

以下字段在 C2 保持 `ModelRequest` 默认值：

```text
context
memory_items
tool_schemas
runtime_metadata
```

`application_metadata` 不自动进入 ModelRequest，也不改写为
`runtime_metadata`。运行元数据属于未来 `RunContext`，由后续 Runtime / Execution
任务明确所有权。

## 5. 非职责

- 不调用 Model 的 `generate` 或 `stream`。
- 不创建 Agent Engine 或推理循环。
- 不执行 Tool，也不组装 Tool Schema。
- 不读取或写入 Memory。
- 不创建 RunContext、run_id、deadline 或 cancellation。
- 不修改 Provider Adapter 和 Provider SDK 请求映射。

## 6. 文件与测试

| 文件 | 职责 |
|---|---|
| `src/agent_kernel/agent/request_builder.py` | C2 纯函数 Builder |
| `src/agent_kernel/agent/__init__.py` | 公开导出 Builder |
| `tests/unit/agent/test_request_builder.py` | 字段映射、默认边界和元数据隔离 |

测试必须证明：

1. Instructions、input 和 output_schema 映射准确。
2. context、memory_items、tool_schemas 和 runtime_metadata 保持默认空值。
3. application_metadata 不会进入 ModelRequest。
4. Builder 不触发 Model 调用。
5. 返回值是独立的严格 `ModelRequest` Schema。

## 7. 验收边界

C2 只关联 K-001。C2 完成后仍不运行 RD-002；真实 Agent 闭环由 C5 验收。
