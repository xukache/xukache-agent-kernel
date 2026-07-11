# 架构变更记录

> 返回总纲：`../architecture.md`

本文记录架构文档和重大设计决策变化。凡是影响系统模块边界、核心数据模型、运行时、消息 / 事件、状态机、Agent 编排、Prompt、Capability、模型策略或观测诊断的变更，都必须在此记录。

## v0.9 - 2026-07-11

- 将 Agent 能力意图统一为 `CapabilityCall`，阶段服务补齐运行身份后构造 `CapabilityRequest`。
- 新增直接执行显式能力白名单的 `DefaultCapabilityGateway` 和 `CapabilityRegistry`。
- 能力名称冻结为 `knowledge.search` 与 `payment.calculate`；政策检索直接调用组合根注入的 `KnowledgeGateway`。
- 删除旧政策工具名、旧同步适配函数、旧工具执行器/注册表和旧能力结果投影；政策证据只从
  `CapabilityResult.output["evidences"]` 进入 WorkflowState 和最终答案。
- Native/LangGraph 继续复用同一阶段服务、能力协议、reducer 和评测数据；离线差分结果为 30/30
  equivalent、0 different。

## v0.8 - 2026-07-11

- 新增框架中立 `KnowledgeGateway`、`KnowledgeQuery`、`KnowledgeSearchResult` 和 `EvidenceItem`。
- 建立 `policy-corpus.v1` 政策基线，包含 tenant、jurisdiction、有效期、审核状态、受众、来源类型、
  文档版本、来源 URL、证据 hash 和语料版本。
- `LexicalKnowledgeGateway` 在 lexical 召回前执行可信元数据过滤；暂不引入向量库、fusion 或 reranker。
- `PolicyRAGTool` 保留为 ToolExecutor 兼容入口，Native/LangGraph 通过组合根复用同一 KnowledgeGateway。
- 模型抽取地区不能覆盖可信检索范围；RAG 专项 eval 独立记录 Recall@K、MRR、引用支持率、
  可信过滤率和无结果安全率。

## v0.7 - 2026-07-10

- `ananhu-agent chat` 直接替换为单栏 Textual TUI；旧逐行命令能力迁移为 action/modal，非交互命令保持兼容。
- 新增框架中立 `RunProgressEvent`、public/transient 安全投影、单点 sequence、gap 失败和唯一终止屏障。
- 新增取消状态与 `user_cancelled`、ObservableModelGateway、显式 reasoning 瞬态路径和 Usage reported 口径。
- CapabilityRequest 补充 run 身份；`other` 采用双运行时等价的确定性无工具非空回复路径。
- reasoning 原文禁止进入业务 trace、状态、报告、badcase、eval 和 differential artifact。
- CLI 组合根读取当前工作目录的 UTF-8 `.env` 并将 provider 密钥保存于当前 Settings 私有映射；
  `RuntimeSettings` 保持显式且不修改进程环境，避免离线 Runtime 与测试受本机配置污染。已导出的
  shell 环境变量继续拥有更高优先级。

## v0.6 - 2026-07-10

- 引入 Provider/Profile 两层模型目录，支持多个 OpenAI-compatible provider 和按模型档位路由。
- 保留 v0.5 环境变量兼容路径；默认 Fake 模型和离线 eval 行为不变。
- API key 继续只通过环境变量读取，禁止进入 profile、trace、测试 fixture 或 artifact。

| 日期 | 变更内容 |
|---|---|
| 2026-07-10 | 发布 v0.5：定义框架中立 async ModelGateway、OpenAI-compatible provider 最小协议、结构化错误和模型 usage；Native/LangGraph 共用组合根，Fake 回归与显式 opt-in 真实 smoke 分开报告。 |
| 2026-07-10 | 发布 v0.4：新增 Native/LangGraph 双运行时差分 runner、`runtime-differential.v1` artifact 和 CLI `eval --runtime both`；仅忽略 runtime 身份、事件 ID、时间、毫秒延迟和内部事件顺序，业务状态、能力参数、证据与安全结果必须一致。 |
| 2026-07-10 | 发布 v0.3：引入最小串行 `LangGraphWorkflowRuntime` 作为默认运行时，保留 `runtime=native` 显式回归选择；图节点只返回 `StatePatch`，项目 reducer 和 CapabilityGateway 继续拥有状态合并与能力治理语义。 |
| 2026-07-10 | 统一架构文档口径：当前实现称为 Native Runtime，未使用旧架构和兼容入口应删除，已发布版本快照保留为审计历史。 |
| 2026-07-10 | 新增 `WorkflowRuntime.invoke()` 端口、`NativeWorkflowRuntime`、Native 阶段服务和 runtime contract suite，CLI 与 EvalRunner 改为依赖 Runtime port，并删除旧 orchestrator 兼容入口。 |
| 2026-07-10 | 新增框架中立 `CapabilityRequest`、`CapabilityResult`、`CapabilityPolicy`、`CapabilityGateway` 端口和 `ToolExecutorCapabilityGateway`，保持 ToolExecutor 治理并为 logical call 重试提供幂等复用。 |
| 2026-07-10 | 新增 `StatePatch`、纯 Python `reduce_workflow_state`、patch 去重、阶段跳转校验、按业务 ID 合并规则，并扩展 `TraceEvent` 的 runtime、node、attempt 和 logical call 字段。 |
| 2026-07-10 | 新增框架中立 `RunRequest`、`WorkflowState`、`WorkflowResult`、`WorkflowPhase`、`RunStatus` 和 `StopReason` 协议。 |
| 2026-07-10 | 建立架构版本快照机制：将 v0.2 完整正文固化为 `versions/v0.2-framework-neutral-baseline.md`，根 `TECH_ARCHITECTURE_MVP.md` 改为稳定版本入口。 |
| 2026-07-10 | 后续架构升级必须新增完整版本正文，并同步更新版本入口、主题分册、实施计划和 changelog，禁止覆盖已发布版本。 |
| 2026-07-10 | 技术路线从旧框架兼容 harness 演进为“LangGraph 默认运行时 + 框架中立业务内核”。 |
| 2026-07-10 | 将早期单轮 Native 编排链路重新定位为可替换 Runtime 实现，不再作为永久唯一状态推进方。 |
| 2026-07-10 | 定义 `WorkflowRuntime`、`RunRequest`、`WorkflowState`、`StatePatch`、`WorkflowResult` 和项目 reducer 边界。 |
| 2026-07-10 | 明确 LangGraph 只负责调度、中断恢复和必要的有限并行，领域状态、Tool、Prompt、Trace、Usage、Badcase 和 Eval 协议由项目维护。 |
| 2026-07-10 | 将当前四 Agent 从永久约束调整为 MVP 实现现状；后续按独立目标、上下文、权限和评测价值决定保留或收敛。 |
| 2026-07-10 | 区分 Case、Session、RunSnapshot、Checkpoint、Trace 和 RunReport 的职责。 |
| 2026-07-10 | 增加能力幂等、可信 jurisdiction、知识元数据过滤、隐私脱敏和 Native/LangGraph contract tests 规则。 |
| 2026-07-10 | 更新 README、AGENTS、API 状态、后端规范和演进计划，旧 Agno 路线不再执行。 |
| 2026-07-10 | 统一 MVP 架构事实源，确认旧 Agno 计划只读归档，并将后续演进入口固定为框架中立 LangGraph 演进计划。 |
| 2026-07-09 | 新增本地政策 fixture、确定性政策检索、一次性伤残补助金测算和引用格式化工具，为后续 Agent 链路提供无外部依赖的 RAG / 测算闭环。 |
| 2026-07-09 | 落地 MVP `ToolRegistry` 和 `ToolExecutor` 最小代码基线：统一工具权限校验、必填输入校验、错误码归一和成功 / 失败 trace 写入，并记录超时、输出 schema、风险策略等后续补齐项。 |
| 2026-07-09 | 统一后端环境管理为 `uv`，固定 Python 版本为 3.11，并通过 `.python-version` 声明。 |
| 2026-07-09 | 创建 MVP Agent 后端项目标准文档体系，确立 CLI MVP、4 Agent、Prompt / Tool / Trace / Eval 治理分册。 |
| 2026-07-09 | 落地 CLI `/trace`、`/badcase` 和 `/feedback bad` 的本地证据收集能力，并补齐 `BadcaseRecord` JSONL 字段。 |
| 2026-07-09 | 落地运行时自动 badcase 候选规则，覆盖低置信意图、RAG 无结果、缺引用、工具失败、不安全回答和空回答。 |
| 2026-07-09 | 增强 `ToolExecutor` 治理能力：补齐 `tool_called` trace、超时、输出必填键校验、重复调用拦截和 `fallback_reason`。 |
| 2026-07-09 | 增强答案治理：支持地区一致性校验、缺引用保守回答、医疗 / 伤残等级承诺和精确金额承诺安全拦截。 |
| 2026-07-09 | 初始化 Python CLI MVP 工程结构。 |
| 2026-07-09 | 落地 `AgentContext`、`AgentMessage`、`ToolCallResult`、`TraceEvent` 等运行时协议。 |
| 2026-07-09 | 增加本地 JSONL trace、metrics、badcase 输出。 |
| 2026-07-09 | 增加早期单轮同步编排链路和 CLI `ask` / `eval` 命令。 |
| 2026-07-09 | MVP 工具先使用本地 fixture RAG 和确定性待遇测算，后续可在不改变 `ToolExecutor` 契约的前提下替换为真实 RAG / 模型。 |
