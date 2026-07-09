# 02. Agent 运行时架构

## 范围

本文定义 Agent 编排、上下文协议、运行时控制、异步边界和 MVP Agent 清单。

## 总体运行时

```text
CLI
  ↓
AgentOrchestrator
  ├── IntentRouterAgent
  ├── IntentReviseRule
  ├── SlotMergeRule
  ├── PromptManager
  ├── ContextManager
  ├── ToolRegistry
  ├── ToolExecutor
  ├── ResultAggregator
  ├── AnswerValidator
  ├── PolicySafetyGuard
  └── TraceRecorder
```

## Agent 清单

MVP 只实现 4 个 Agent：

| Agent | 职责 |
|---|---|
| `IntentRouterAgent` | 意图识别、槽位抽取、低置信度追问 |
| `PolicyRAGAgent` | 法规检索和引用依据组织 |
| `DomainConsultationAgent` | 政策咨询类回答 |
| `PaymentCalculationAgent` | 待遇测算解释和计算工具调用 |

## Agent 无状态原则

- Agent 不直接写会话状态。
- Agent 不互相直接调用内部方法。
- Agent 通过 `AgentContext` 读取上下文，通过 `AgentMessage` 返回结构化结果。
- `AgentOrchestrator` 是唯一允许合并上下文和推进状态的组件。

## 上下文协议

核心结构：

```text
AgentContext
  ├── request
  ├── conversation
  ├── intent_result
  ├── agent_plan
  ├── tool_results
  ├── agent_outputs
  ├── draft_final_answer
  ├── verification_result
  ├── safety_result
  └── final_answer
```

## 路由策略

```text
IntentRouterAgent 原始识别
  ↓
IntentReviseRule 规则修正
  ↓
SlotMergeRule 合并 active_slots
  ↓
AgentOrchestrator 生成 AgentPlan
```

复合意图在 MVP 串行处理，不做并行 Agent。

## 异步与流式边界

MVP 外部表现为单轮同步咨询。

允许：

- async I/O 调用模型。
- async I/O 调用 RAG。
- async I/O 写入本地存储。

不做：

- 后台任务队列。
- 并行 Agent 仲裁。
- 任务暂停、取消、复杂 resume。
- WebSocket 多路事件流。
- 用户中途插队问题。

流式输出只作为后续体验增强，不作为 MVP 核心架构。

