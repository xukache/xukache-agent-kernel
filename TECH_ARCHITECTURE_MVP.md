# 安安虎工伤智能助手 Agent Harness 技术架构（MVP v0.2）

## 0. 文档信息

| 字段 | 内容 |
|---|---|
| 状态 | 当前 MVP 架构基线 |
| 版本 | v0.2 |
| 更新日期 | 2026-07-10 |
| 技术路线 | LangGraph 默认运行时 + 框架中立业务内核 |
| 当前实现 | Native Runtime、四 Agent 离线闭环、CLI、JSONL 运行证据 |
| 当前限制 | 未接入 LangGraph、真实模型和生产知识库 |

本文件描述当前有效的 MVP 架构。详细且持续维护的规则位于 `docs/architecture/`；冲突时以分册和 `docs/architecture/99-changelog.md` 中较新的决策为准。

## 1. 架构目标

系统首先是一个可信的工伤咨询 Agent Harness，而不是某个 Agent 框架的示例工程。它需要长期支持政策咨询、案件事实管理、地区知识路由、混合检索、待遇辅助测算、多步推理、流式事件、多模态能力、全链路 trace、token 计量、badcase 和评测闭环。

第一性原理下，稳定资产是：

- 案件事实、事实来源和确认状态。
- 服务地市、政策适用范围和知识证据。
- 业务状态转换、停止原因和错误语义。
- Agent、Capability、Prompt、Response 的项目协议。
- Trace、Usage、Badcase、Eval 等运行证据。

LangGraph、模型供应商、向量库和存储实现都是可替换基础设施。

## 2. 当前范围与演进范围

### 2.1 当前已实现

- CLI `ask`、`chat`、`eval` 和反馈闭环。
- `IntentRouterAgent`、`PolicyRAGAgent`、`DomainConsultationAgent`、`PaymentCalculationAgent`。
- `AgentOrchestrator` 驱动的单轮/轻量多轮 Native Runtime。
- `PromptManager`、`ContextManager`、`ToolRegistry`、`ToolExecutor`。
- Fake Model、fixture policy RAG、确定性待遇测算。
- Session、Trace、TaskState、RunReport、Badcase 和分层 Eval。

这些能力证明离线协议和工程闭环可运行，不证明真实模型输出质量、生产政策知识质量或 LangGraph 恢复能力。

### 2.2 本轮架构演进目标

- 从共享 `AgentContext` 演进为 `RunRequest + WorkflowState + StatePatch + WorkflowResult`。
- 从固定 `AgentOrchestrator` 所有权演进为框架中立 `WorkflowRuntime` 端口。
- 将当前编排器保留为 `NativeWorkflowRuntime`。
- 在协议稳定后增加 `LangGraphWorkflowRuntime`，作为默认可配置运行时。
- 使用相同 contract tests、eval cases 和 trace 语义比较两个运行时。

### 2.3 当前非目标

- HTTP API、WebSocket、前端和小程序接入。
- 复杂后台任务平台和通用 DAG 平台。
- 为每个现有 Agent 创建子图。
- 在没有真实恢复需求前建设多套 checkpoint 存储。
- 为展示多 Agent 而拆分更多专项 Agent。

## 3. 总体架构

```text
CLI / future interfaces
        |
        v
Application Use Cases
        |
        +--> Domain Policies / State Transition Rules
        +--> AgentRunner / PromptContextService
        +--> CapabilityGateway
        +--> KnowledgeGateway / ModelGateway
        +--> TraceSink / UsageLedger / RunRepository
        |
        v
WorkflowRuntime Port
        +--> NativeWorkflowRuntime
        +--> LangGraphWorkflowRuntime
```

推荐目标目录：

```text
ananhu_agent/
  domain/
  application/
  ports/
  runtimes/
    native/
    langgraph/
  infrastructure/
  interfaces/
```

当前目录按任务增量迁移，禁止为了目录整齐进行一次性重写。

## 4. 三个架构平面

### 4.1 控制面

负责请求如何推进：

- 工作流阶段和条件路由。
- 模型与能力调用。
- 重试、终止、中断和有限并行。
- Native 或 LangGraph 运行时选择。

### 4.2 状态面

负责系统记住什么以及恢复什么：

- `CaseRecord`：跨会话案件事实。
- `SessionRecord`：连续对话状态。
- `WorkflowState`：单次 run 的可序列化业务状态。
- `CheckpointEnvelope`：运行时恢复快照。
- `MemoryEntry`：有来源、有效期和失效规则的工作记忆。

### 4.3 证据面

负责系统如何被审计、计量和评测：

- `TraceEvent`：只追加事件时间线。
- `RunReport`：单次运行摘要。
- `UsageRecord`：模型、检索和能力用量。
- `BadcaseRecord`：失败分类和修复闭环。
- `EvaluationArtifact`：可复现评测证据。

三个平面可以关联，但不能使用同一存储对象代替彼此。

## 5. 工作流设计

### 5.1 稳定业务阶段

图表达业务阶段，不表达 Agent 清单：

```text
receive_request
  -> understand_request
  -> merge_case_facts
  -> validate_required_facts
  -> clarify | resolve_jurisdiction
  -> plan_capabilities
  -> retrieve_or_calculate
  -> validate_evidence
  -> compose_response
  -> safety_check
  -> complete
```

简单咨询可以跳过不需要的阶段。复杂需求未来可以在 `plan_capabilities` 后有限并行，但所有分支必须使用相同的案件事实版本和 jurisdiction scope。

### 5.2 调度权与状态语义

目标运行时规则：

- Native Runtime 或 LangGraph Runtime 拥有调度权。
- 项目定义的 transition policy 和 reducer 拥有业务状态合并语义。
- Agent 或阶段服务返回 `AgentOutcome` 或 `StatePatch`，不得原地修改共享状态。
- 每个状态字段必须有明确写入者、合并规则和失效规则。

当前兼容实现仍由 `AgentOrchestrator` 原地推进 `AgentContext`，Agent 返回 `AgentMessage` 和 `ToolCallRequest`。该协议在任务 26-29 完成前继续有效，不应被误写成已经迁移。

### 5.3 停止原因

至少区分：

```text
completed
clarification_required
insufficient_evidence
jurisdiction_unresolved
capability_failed
safety_blocked
step_limit_reached
retry_limit_reached
cancelled
internal_error
```

`status`、`phase` 和 `stop_reason` 分开建模，避免将所有未完成情况归为模糊失败。

## 6. LangGraph 使用边界

### 6.1 允许 LangGraph 负责

- 节点注册、边和条件路由。
- 单次 run 内的状态推进。
- interrupt、resume 和人工确认触发。
- 节点级重试和必要的有限并行。
- 运行时 checkpoint 的读写适配。

### 6.2 禁止 LangGraph 拥有

- 领域实体和案件事实结构。
- Agent、Capability、Prompt、Evidence、Response 公共协议。
- 业务 reducer、错误码和停止原因语义。
- Tool 权限、幂等、超时和重试策略。
- session/case/run 标识规则。
- 项目 trace、usage、badcase 和 eval schema。
- 唯一可读的 checkpoint 数据格式。

### 6.3 类型隔离

以下类型只能出现在 `runtimes/langgraph/` 和组合根：

```text
StateGraph
Command
RunnableConfig
LangGraph message/channel/checkpoint types
```

LangGraph state 是 `WorkflowState` 的运行时投影，不是领域事实源。

## 7. 核心项目协议

### 7.1 请求和状态

```text
RunRequest
  request_id
  session_id
  case_id
  message_id
  text
  attachments
  trusted_jurisdiction
  consent_scope

WorkflowState
  schema_version
  run_id
  phase
  status
  case_facts
  intent_result
  execution_plan
  capability_results
  evidence
  draft_response
  validation_result
  safety_result
  stop_reason

StatePatch
  fact_updates
  evidence_updates
  capability_updates
  response_update
  next_phase
  stop_reason
```

`trusted_jurisdiction` 只能来自可信业务输入或用户明确选择。模型提取的 `mentioned_region` 只能作为候选事实，不能直接改变权限或知识库边界。

### 7.2 Agent 协议

```text
AgentInput
AgentOutcome
AgentDecision
AgentDescriptor
AgentError
```

允许的决策收敛为：`route`、`request_information`、`invoke_capability`、`delegate`、`respond`、`fail`。

当前四 Agent 作为 MVP 实现继续保留，但长期是否独立取决于是否具备独立目标、上下文、权限和评测价值。`PolicyRAGAgent` 和 `PaymentCalculationAgent` 可在后续演进为应用服务或 Capability，不强制保持 Agent 身份。

### 7.3 能力协议

```text
CapabilitySpec
CapabilityRequest
CapabilityExecutionContext
CapabilityResult
CapabilityError
CapabilityPolicy
```

`CapabilityResult` 至少包含 `status`、结构化 `data`、`evidence`、`capability_version`、`input_digest`、`duration_ms`、`retryable` 和 `error_code`。

## 8. Tool 与能力治理

现有 `ToolExecutor` 已实现注册、输入必填校验、调用方白名单、进程内重复调用拦截、超时、输出必填校验和工具 trace。

目标 `CapabilityGateway` 在保留上述能力的基础上补齐以下治理链路：

```text
显式注册
  -> schema 校验
  -> 权限和 jurisdiction 检查
  -> 幂等检查
  -> 超时/重试策略
  -> 执行
  -> 结果 schema 校验
  -> 脱敏
  -> trace + usage
```

目标调用协议使用稳定关联字段：

```text
run_id
node_id
attempt
capability_call_key
capability_version
```

图节点重试不得产生不可解释的重复副作用。检索、计算和未来写操作必须声明各自幂等等级。

## 9. 模型与知识检索

### 9.1 ModelGateway

业务代码依赖模型能力 profile，不依赖供应商 SDK。统一记录模型、参数、token、延迟、缓存和错误信息。Provider cache 只是性能优化，不能影响业务正确性。

### 9.2 KnowledgeGateway

知识检索在召回前执行可信元数据过滤：

```text
tenant
+ jurisdiction
+ effective_at
+ review_status
+ audience_role
+ source_type
+ document_version
```

目标检索链路：

```text
metadata filter
  -> lexical retrieval
  -> vector retrieval
  -> fusion
  -> rerank
  -> citation validation
```

MVP 可以使用确定性检索，但输出必须是结构化 `EvidenceItem`，包含来源、条款、地区、效力时间、版本、内容摘要和检索得分。无充分证据时必须追问、限定回答或拒答。

## 10. Prompt、上下文和记忆

- Prompt 由稳定段、半稳定段和动态段组成，并带版本和变更说明。
- ContextManager 按证据等级分配 token 预算，不按时间粗暴截断。
- 当前请求、已确认关键事实、安全规则和直接支撑结论的证据不可被静默裁掉。
- 记忆不是聊天历史，也不是知识库。
- 每条事实带来源、确认状态、置信度、有效期和替代关系。
- 案件事实、地区、政策语料版本或公式版本变化时，相关检索和测算快照必须失效。

每次构建上下文输出 `ContextBuildReport`，记录候选项、入选项、token、裁剪原因和淘汰证据 ID。

## 11. 状态、Checkpoint 与恢复

```text
CaseRecord       跨 session 的业务案件事实
SessionRecord    连续对话和低风险工作记忆
RunSnapshot      当前 run 的审计投影
Checkpoint       运行时恢复数据
TraceEvent       不可变过程证据
RunReport        最终统计摘要
```

恢复的是带 `schema_version` 的可序列化 `WorkflowState`。恢复前检查 runtime、Prompt、Tool Registry、政策语料和状态 schema 版本。无法安全迁移时必须停止恢复并给出明确原因。

## 12. 观测、用量和评测

项目 trace 是权威业务证据。LangGraph/LangSmith 事件通过映射器补充 `runtime_name`、`runtime_node`、`attempt`、`checkpoint_id`，不能替代项目事件。

评测按机制分层：

- 路由：意图、复合需求和流程选择。
- 事实：抽取、冲突发现和确认状态。
- RAG：地区/时效过滤、召回、排序、引用和结论支持率。
- 测算：输入、公式版本、误差和缺失输入处理。
- 答复：事实一致性、不确定性披露和安全边界。
- Runtime：状态转换、重试、恢复、幂等和 trace 完整性。
- 成本：token、模型调用、能力调用和延迟。

Native 与 LangGraph Runtime 必须运行同一 contract tests 和 eval cases，比较最终语义、关键状态转换、能力调用和 trace，而不是要求框架内部事件完全一致。

## 13. 对外接口边界

当前 CLI 是开发与验收入口。应用层用例不得依赖 Typer，因此未来 HTTP、WebSocket、语音或其他入口可以复用同一 `RunRequest`、流式事件和 `WorkflowResult` 协议。

当前不实现公开 API。具体状态和启用条件见 `docs/api-contracts.md`。

## 14. 技术栈

| 类别 | 选择 |
|---|---|
| Python | 3.11 |
| 环境与依赖 | uv |
| 数据协议 | Pydantic |
| CLI | Typer |
| 默认工作流运行时 | LangGraph，待协议重构完成后接入 |
| 当前运行时 | Native AgentOrchestrator |
| 测试 | pytest |
| 当前持久化 | JSONL |
| Prompt | YAML + 版本元信息 |

不把具体模型 SDK、向量库或 LangSmith 设为领域层依赖。

## 15. 演进顺序

```text
修正文档事实源
  -> 定义框架中立状态和增量协议
  -> 拆分 Native Runtime 阶段函数
  -> 定义 WorkflowRuntime 端口和 contract tests
  -> 接入最小串行 LangGraph Runtime
  -> 双运行时回归与 trace 对齐
  -> 接入真实 ModelGateway 和政策 KnowledgeGateway
  -> 有真实需求后启用 checkpoint、interrupt 和有限并行
```

禁止先安装 LangGraph，再让现有 `AgentContext` 直接成为 Graph State。

## 16. 主要风险与应对

| 风险 | 应对 |
|---|---|
| LangGraph 类型泄漏 | 依赖规则、适配器边界和导入检查 |
| Native 与 LangGraph 双状态机 | Native 降为 `WorkflowRuntime` 实现，不在图节点中完整调用旧 orchestrator |
| 节点重试重复调用 | 稳定 call key、幂等等级和持久化执行记录 |
| checkpoint 冒充业务状态 | 明确 checkpoint/session/case/trace 生命周期和权威关系 |
| 多 Agent 过度拆分 | 用独立目标、上下文、权限和评测价值作为拆分门槛 |
| 过期政策或测算被复用 | 版本、有效期、事实变更触发失效 |
| fake 指标被误报为业务效果 | 离线 contract/eval 与真实模型/RAG smoke 分开报告 |

## 17. MVP 验收边界

当前 MVP 验收包括：

- `uv run pytest -v` 通过。
- CLI 咨询、会话、反馈和 eval 可运行。
- 工具治理、Prompt、上下文、安全、trace、badcase 和分层指标有测试。
- 当前离线 Native Runtime 行为可复现。

LangGraph阶段额外要求：

- Native 与 LangGraph Runtime 通过同一 contract tests。
- LangGraph 公共边界不泄漏框架类型。
- 状态增量、停止原因、能力调用和 trace 语义一致。
- checkpoint 未启用时不得宣称支持跨进程恢复。

真实业务验收还需要真实模型、受治理政策语料、检索评测和专家标注，不属于当前离线 harness 已完成事实。
