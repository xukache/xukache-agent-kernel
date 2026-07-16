# C2 Instructions 与 ModelRequest 组装实现计划

> 本计划只执行已由用户确认的 C2 设计，不改变 `DEV_SPEC.md` 的架构边界。

## 目标

实现 `build_model_request(definition, agent_input)`，将 C1 的 Agent Definition /
Input 转换为 B1 的 Provider Neutral `ModelRequest`。

## 步骤

1. 先编写 Builder 的失败测试，覆盖字段映射、默认字段、元数据隔离和不调用 Model。
2. 实现 `src/agent_kernel/agent/request_builder.py` 中的无状态纯函数。
3. 从 `agent_kernel.agent` 导出 Builder。
4. 运行 C2 单元测试、全量测试、锁文件检查、构建和差异检查。
5. 更新活动文档为“C2 已实现，待用户验收”；用户确认后再提交和合并。

## 明确不做

- 不实现 Agent Engine、Model 调用或推理循环。
- 不引入 Tool、Memory、Runtime 或 RunContext。
- 不运行或伪造 RD-002。
