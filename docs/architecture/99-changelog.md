# 架构变更记录

## 2026-07-10

- 技术路线从 Agno-compatible harness 演进为“LangGraph 默认运行时 + 框架中立业务内核”。
- 将现有 `AgentOrchestrator` 定位为 Native Runtime，不再作为永久唯一状态推进方。
- 定义 `WorkflowRuntime`、`RunRequest`、`WorkflowState`、`StatePatch`、`WorkflowResult` 和项目 reducer 边界。
- 明确 LangGraph 只负责调度、中断恢复和必要的有限并行，领域状态、Tool、Prompt、Trace、Usage、Badcase 和 Eval 协议由项目维护。
- 将当前四 Agent 从永久约束调整为 MVP 实现现状；后续按独立目标、上下文、权限和评测价值决定保留或收敛。
- 区分 Case、Session、RunSnapshot、Checkpoint、Trace 和 RunReport 的职责。
- 增加能力幂等、可信 jurisdiction、知识元数据过滤、隐私脱敏和 Native/LangGraph contract tests 规则。
- 更新 README、AGENTS、API 状态、后端规范和后续任务计划，旧 Agno 任务 25-31 不再执行。

> 返回总纲：`../architecture.md`

本文记录架构文档和重大设计决策变化。凡是影响系统模块边界、核心数据模型、运行时、消息 / 事件、状态机、Agent 编排、Prompt、Tool、模型策略或观测诊断的变更，都必须在此记录。

| 日期 | 变更内容 |
|---|---|
| 2026-07-09 | 新增本地政策 fixture、确定性政策检索、一次性伤残补助金测算和引用格式化工具，为后续 Agent 链路提供无外部依赖的 RAG / 测算闭环。 |
| 2026-07-09 | 落地 MVP `ToolRegistry` 和 `ToolExecutor` 最小代码基线：统一工具权限校验、必填输入校验、错误码归一和成功 / 失败 trace 写入，并记录超时、输出 schema、风险策略等后续补齐项。 |
| 2026-07-09 | 统一后端环境管理为 `uv`，固定 Python 版本为 3.11，并通过 `.python-version` 声明。 |
| 2026-07-09 | 创建 MVP Agent 后端项目标准文档体系，确立 CLI MVP、4 Agent、Prompt / Tool / Trace / Eval 治理分册。 |
| 2026-07-09 | 落地 CLI `/trace`、`/badcase` 和 `/feedback bad` 的本地证据收集能力，并补齐 `BadcaseRecord` JSONL 字段。 |
| 2026-07-09 | 落地运行时自动 badcase 候选规则，覆盖低置信意图、RAG 无结果、缺引用、工具失败、不安全回答和空回答。 |
| 2026-07-09 | 增强 `ToolExecutor` 治理能力：补齐 `tool_called` trace、超时、输出必填键校验、重复调用拦截和 `fallback_reason`。 |
| 2026-07-09 | 增强答案治理：支持地区一致性校验、缺引用保守回答、医疗 / 伤残等级承诺和精确金额承诺安全拦截。 |

## 2026-07-09

- 初始化 Python CLI MVP 工程结构。
- 落地 `AgentContext`、`AgentMessage`、`ToolCallResult`、`TraceEvent` 等运行时协议。
- 增加本地 JSONL trace、metrics、badcase 输出。
- 增加 `AgentOrchestrator` 单轮同步链路和 CLI `ask` / `eval` 命令。
- MVP 工具先使用本地 fixture RAG 和确定性待遇测算，后续可在不改变 ToolExecutor 契约的前提下替换为真实 RAG / 模型。
