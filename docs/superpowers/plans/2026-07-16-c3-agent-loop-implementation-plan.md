# C3 最小 Agent 推理循环实现计划

> 本计划只执行已由用户确认的 C3 设计，不改变 `DEV_SPEC.md` 的架构边界。

## 目标

实现一次 `AgentInput -> Model -> AgentResult` 的异步最小链路。

## 步骤

1. 编写失败测试，覆盖成功、结构化输出、Model 错误、取消、内部错误和未支持
   Tool Call。
2. 实现 `run_agent`，复用 C2 Builder 和 B2 Model Contract。
3. 从 `agent_kernel.agent` 导出 `run_agent`。
4. 运行 C3 单元测试、全量测试、锁文件检查、构建和差异检查。
5. 更新活动文档为“C3 已实现，待用户验收”；用户确认后再提交和合并。

## 明确不做

- 不实现多轮循环或 `max_model_rounds`。
- 不执行 Tool、Memory 或 Runtime。
- 不运行或伪造 RD-002。
