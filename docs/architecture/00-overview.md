# 00. 项目概览

## 项目定位

安安虎工伤智能助手是工伤咨询领域的 Agent Harness。系统目标不是展示 Agent 数量，而是把需求理解、案件事实、政策证据、受治理能力、安全校验和评测组织成可解释、可恢复、可替换运行时的执行链。

## 当前实现

- CLI 作为开发和验收入口。
- 四个 MVP Agent 和 `AgentOrchestrator` Native Runtime。
- Prompt、上下文、工具、模型 profile、session 和 JSONL 运行证据。
- fake model、fixture policy RAG、确定性测算和 30 条以上 eval cases。

当前实现是可回归的离线 harness，不等同于真实模型和生产知识库已经可用。

## 目标分层

```text
interfaces       CLI 和未来外部入口
application      用例、工作流阶段、状态转换和响应组装
domain           案件事实、地区、政策适用、测算和安全规则
ports            Runtime、Model、Knowledge、Capability、Trace、Usage
runtimes         Native 和 LangGraph 实现
infrastructure   模型、检索、存储、观测和安全适配
```

依赖只允许从外向内。LangGraph 位于 `runtimes/langgraph`，不得成为 domain/application 的依赖。

## 三个平面

| 平面 | 职责 |
|---|---|
| 控制面 | 工作流、路由、模型/能力调用、重试和终止 |
| 状态面 | case、session、run state、checkpoint 和记忆 |
| 证据面 | trace、usage、report、badcase 和 eval artifact |

## 当前 Agent 定位

| Agent | 当前职责 | 长期判断 |
|---|---|---|
| `IntentRouterAgent` | 意图和槽位抽取 | 可保留为理解能力或节点服务 |
| `PolicyRAGAgent` | 生成政策检索请求 | 可演进为 KnowledgeGateway 应用服务 |
| `DomainConsultationAgent` | 领域答复 | 作为核心生成/决策能力保留候选 |
| `PaymentCalculationAgent` | 生成测算请求 | 可演进为确定性计算应用服务 |

只有具备独立目标、上下文、权限和评测价值时，能力才应保持为独立 Agent。

## 当前非目标

- HTTP API、WebSocket、前端和小程序。
- 在框架中立状态协议前安装并直接使用 LangGraph。
- 每个 Agent 一个节点或一个子图。
- 通用 planner、开放式无限 ReAct 循环和复杂并行仲裁。
- 将聊天历史、checkpoint 或模型摘要当作案件事实来源。

## 参考设计的使用原则

项目吸收现代 Agent Harness 中控制/状态/证据分离、工具治理、上下文预算、运行恢复和机制专项评测等原则。Code Agent 的 shell、文件沙箱、workspace diff 等特有能力不照搬；对应地，本项目重点治理 jurisdiction、政策时效、PII、案件事实冲突、测算幂等和证据完整性。
