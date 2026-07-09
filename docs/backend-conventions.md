# 后端开发规范

本文定义安安虎工伤智能助手 Agno CLI MVP 的后端工程规则。当前项目尚未初始化代码结构，本规范用于后续实现阶段约束模块边界。

## 项目形态

- Python 后端型 Agent CLI 项目。
- 不使用 Dify。
- 基于 Agno 实现 Agent、Tool、Memory、Storage 和模型适配。
- 当前不做 Web API 和前端。

## 推荐模块边界

后续实现时建议按以下边界组织：

```text
ananhu_agent/
  cli/                 # CLI 入口和命令解析
  orchestrator/        # AgentOrchestrator、路由和运行时控制
  agents/              # 4 个 MVP Agent
  context/             # AgentContext、ContextManager、槽位合并
  prompts/             # prompt 模板和 PromptManager
  tools/               # ToolRegistry、ToolExecutor、业务工具
  models/              # ModelRouter、ModelClient
  storage/             # TaskState、Trace、Report、Badcase、Eval 存储
  evaluation/          # eval runner、指标计算
  config/              # Pydantic Settings、YAML 配置
```

## Agent 规则

- Agent 不直接写 session state。
- Agent 不直接调用底层工具函数。
- Agent 不直接拼接完整 prompt。
- Agent 输出必须结构化，优先返回 `AgentMessage` 或等价 schema。
- 新增 Agent 前必须满足拆分条件：高频 badcase、独立工具链、独立评测指标、独立 Prompt / 规则同时成立。

## Tool 规则

- 所有工具必须注册到 `ToolRegistry`。
- 所有工具调用必须经过 `ToolExecutor`。
- 工具必须声明 `risk_level`、`timeout_ms`、`allowed_callers`、`input_schema`、`output_schema`。
- 工具失败必须返回统一错误码，不允许抛出不可解释异常给最终用户。
- 每次工具调用必须写入 trace。

## Prompt 规则

- Prompt 不允许硬编码在 Agent 类中。
- Prompt 必须有 `prompt_id`、`version`、`agent`、`task_type`、`model_profile`、`output_schema`、`failure_policy`。
- Prompt 必须按固定分区组织：任务、规则、输入 schema、上下文、证据 / 工具结果、输出 schema、失败策略。
- 修改 Prompt 必须运行对应 eval case，并记录是否需要回滚。

## 异步边界

- 允许使用 async I/O 调用模型、RAG、存储或文件系统。
- MVP 不做后台任务队列。
- MVP 不做并行 Agent 仲裁。
- MVP 不做任务暂停、取消、复杂 resume。
- 流式输出仅作为后续体验增强，不作为 MVP 核心架构。

## 测试与验证

后续代码实现后，至少需要覆盖：

- Intent / slot schema 校验。
- ToolExecutor 参数校验、错误码和 trace。
- PromptManager 模板解析和版本选择。
- ContextManager 分区裁剪，不裁剪 `current_query`。
- PolicySafetyGuard 高风险表达拦截。
- eval runner 指标输出。

具体命令待 Python 项目初始化后补充。

