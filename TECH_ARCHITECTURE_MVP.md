# 安安虎工伤智能助手 Agno 多 Agent 重构版技术架构（MVP v0.1）

## 0. 文档版本信息

| 字段 | 内容 |
|---|---|
| 文档版本 | MVP v0.1 |
| 创建日期 | 2026-07-08 |
| 当前阶段 | 无前端交互式 CLI MVP |
| 技术路线 | 不使用 Dify，基于 Agno 自研多 Agent 编排 |
| 适用范围 | MVP 技术架构设计、业务流程、数据流、Agent 协作、上下文协议、评测与治理设计 |
| 非目标 | 本版本不创建代码结构、不实现业务代码、不接入前端 |

### 0.1 版本管理约定

技术架构文档按版本演进，避免后续迭代反复覆盖历史设计：

```text
TECH_ARCHITECTURE.md          # 当前工作版本，始终指向最新架构说明
TECH_ARCHITECTURE_MVP.md      # 后续可固化的 MVP 版本快照
TECH_ARCHITECTURE_V0.2.md     # 后续增强版，例如加入 FastAPI API 层
TECH_ARCHITECTURE_V0.3.md     # 后续增强版，例如加入语音 / 图片 Agent
```

Git 分支约定：

```text
mvp          # CLI MVP 版本主线
v0.2-api     # 后续 FastAPI / WebSocket 服务化版本
v0.3-prod    # 后续多地市部署、监控和运维增强版本
```

每次架构升级需要记录：

- 新增能力。
- 删除或暂缓能力。
- 数据模型变化。
- Agent 分工变化。
- 工具调用变化。
- 评测指标变化。
- 对旧版本的兼容性影响。

## 1. 文档目标

本文档用于指导基于现有 `ananhu_common-main` 项目，重新设计并实现一个不依赖 Dify、完全基于 Agno 框架的行业多 Agent 系统。

第一阶段目标不是直接复刻线上小程序后端，而是先实现一个无前端交互式 CLI 版本，跑通完整 Agent 闭环：

```text
用户输入
  ↓
意图识别
  ↓
任务拆解与 Agent 路由
  ↓
知识检索 / 工具调用 / 模型生成
  ↓
结果聚合与校验
  ↓
交互式 CLI 输出
  ↓
Trace、评测、badcase 记录
```

## 2. 可行性判断：Agno 是否适合

结论：可行，而且适合做当前项目的重构版。

Agno 提供 Agent、Team、Workflow、Tools、Knowledge、Memory、Storage、Metrics 和 AgentOS 等能力，适合构建多 Agent 系统。对本项目最关键的是：

- **多 Agent 编排：** 可以用 Team 或 Workflow 表达多个专家 Agent 的协作关系。
- **多模型适配：** 不同 Agent 可以绑定不同模型，例如简单意图分类用低成本模型，复杂法规推理用强推理模型。
- **工具调用：** RAG 检索、待遇测算、隐患识别、语音识别都可以封装为 Agno Tool。
- **状态管理：** 可以用 session state、memory 和 storage 保存会话上下文、用户画像、trace 和 badcase。
- **CLI 友好：** 第一版无需前端，可以直接通过 CLI 输入问题、观察路由、检索、调用工具和最终回答。

需要注意：

- Agno 不能自动解决业务拆分、评测指标、知识库质量和工具设计问题，这些仍需要系统设计。
- 如果直接把每个功能包成 Agent，而没有路由、记忆、评测和监控，仍然会变成「多 Agent 名词包装」。
- 第一版应控制范围，优先做「工伤咨询 + 本地 RAG + 待遇测算 + CLI trace」的小闭环。
- MVP 不追求 Agent 数量多，只保留 4 个职责差异明确的核心 Agent。工伤认定、劳动能力鉴定、参保认定等文本咨询先统一归入 `DomainConsultationAgent`，后续根据真实 badcase 再决定是否拆分。

## 3. 参考现有项目能力

现有 `ananhu_common-main` 已有以下可复用业务资产：

| 现有能力 | 当前位置 | 重构后处理方式 |
|---|---|---|
| 工伤政策文档和地方政策 | `data/documents/` | 迁移为 Knowledge / RAG 数据源 |
| Milvus 向量检索 | `rag/vector_store/`、`rag/tools/rag_tool.py` | 抽象成 `PolicyRAGTool` |
| 混合检索与重排序 | `hybrid_retriever.py`、`bge_reranker.py` | 保留思路，重构接口 |
| 工伤认定、参保认定、劳动能力鉴定任务分类 | `rag/rag_config.py` | 作为意图分类和 Agent 路由基础 |
| 待遇测算 | `payment_evaluation_service.py` | 抽象成 `PaymentCalculationTool` |
| 隐患识别 | `hdanger_service.py` | 第一版 CLI 可先预留，不作为 P0 |
| 语音识别 | `call_service.py`、FunASR | CLI 第一版不做语音，P1 再接 |
| 内容安全 | 百度 / 阿里云内容安全 | CLI 第一版预留审核接口，P1 接入 |
| WebSocket 流式协议 | `chat_service.py` | CLI 第一版不需要，后续 API 版再做 |

## 4. 平台类型与阶段范围

### 4.1 平台类型

第一阶段是 CLI Agent 应用，不包含前端、不包含 WebSocket、不包含政府小程序适配。

后续演进：

```text
CLI MVP
  ↓
本地评测与 trace
  ↓
FastAPI Agent 服务
  ↓
WebSocket / 小程序接入
  ↓
多地市部署与监控看板
```

### 4.2 第一阶段 CLI MVP 范围

P0 只做能证明「完整多 Agent 闭环」的最小范围：

1. 文本输入。
2. 意图识别。
3. Agent 路由，MVP 只路由到 4 个核心 Agent。
4. 工伤法规 RAG 检索。
5. 工伤认定 / 劳动能力鉴定 / 待遇测算 3 类任务。
6. 多模型配置。
7. 结果聚合与依据校验。
8. CLI 输出 trace。
9. 最小评测集与 badcase 记录。

不做：

- 前端页面。
- WebSocket。
- 语音输入。
- 图片识别。
- OSS 报告导出。
- 线上权限系统。
- 完整内容安全服务。

这些放到 P1 / P2。

### 4.2.1 异步与流式边界

MVP 不做复杂异步任务架构。系统外部表现为单轮同步咨询：用户输入一个问题，`AgentOrchestrator` 完成路由、工具调用、校验和最终回答后返回。

允许使用 async I/O 来实现模型调用、RAG 检索、数据库读写和文件写入，但不引入后台任务队列、并行 Agent 调度、任务暂停 / 取消 / resume、任务句柄或多路 WebSocket 事件流。

流式输出不是 MVP 核心目标。若后续需要改善 CLI 体验，可以只在最终答案生成阶段做轻量 streaming：

```text
意图识别 -> RAG / 测算工具 -> 答案聚合 -> 最终回答流式打印
```

这仍然是同步主流程，只是展示方式变成边生成边打印。Trace 记录最终完整回答，不记录每个 token。

MVP 明确不做：

- 后台 Agent 持续运行。
- 多 Agent 并行执行和仲裁。
- 用户中途插队提问。
- 任务暂停、恢复、取消。
- WebSocket 多路事件流。
- 复杂异步调度器。

### 4.3 MVP Agent 收敛原则

MVP 不按业务名词拆 Agent，而按职责差异拆 Agent。如果两个模块的输入、工具、模型要求、评测指标和失败模式都相似，就先合并。

MVP 只保留：

| Agent | 保留原因 |
|---|---|
| `IntentRouterAgent` | 负责意图识别、槽位抽取和低置信度判断，是所有后续路由的入口。 |
| `PolicyRAGAgent` | 负责法规和地方政策检索，是政务咨询可信度的核心。 |
| `DomainConsultationAgent` | 统一处理工伤认定、劳动能力鉴定、参保认定等文本咨询，避免早期过度拆分。 |
| `PaymentCalculationAgent` | 待遇测算是结构化计算任务，和普通政策问答差异明显，应单独拆分。 |

MVP 不在 Agent 清单中列出“未来可能拆分的 Agent”。工伤认定、劳动能力鉴定、参保认定先通过 `DomainConsultationAgent + task_type` 承接；答案校验、信息追问、安全守卫先用规则或函数承接；语音和图片输入不进入 CLI MVP。

后续是否拆分，只看真实证据：高频 badcase、独立工具链、独立评测指标、独立 Prompt / 规则同时成立时，才从现有 Agent 中拆出新 Agent。

### 4.4 参考项目可接入设计

本节基于 `饮食推荐Agent` 和 `EchoMind面试型多agent项目` 的设计进行取舍。接入原则是：只吸收能增强 MVP 工程闭环的设计，不因为“多 Agent”概念而扩大 Agent 数量。

#### 4.4.1 MVP 建议接入

| 来源 | 设计 | 安安虎 MVP 接入方式 | 接入原因 |
|---|---|---|---|
| 饮食推荐 Agent | Orchestrator 持有状态，Worker Agent 无状态 | `AgentOrchestrator` 作为唯一状态写入方；各 Agent 只接收 `AgentContext` 并返回结构化结果 | 避免 Agent 内部 memory 与会话状态不一致，也便于 CLI trace 回放 |
| 饮食推荐 Agent | 意图识别后增加规则二次矫正 | `IntentRouterAgent` 输出后进入 `IntentReviseRule`，修正低置信度、关键词强命中、复合意图 | 政务场景不能完全依赖 LLM 分类，规则兜底能提升稳定性 |
| 饮食推荐 Agent | 槽位字典约束与多轮槽位合并 | 建立工伤咨询槽位字典，LLM 只能输出合法枚举；多轮对话采用 current 覆盖 history、空值保留 history | 适合工伤认定、劳动能力鉴定、待遇测算的材料补全和追问 |
| 饮食推荐 Agent | Trace 作为单一事实来源 | 每轮 CLI 对话保存 `trace_id`、事件时间线、Agent I/O、工具调用、latency、token、fallback 标记 | 支撑 badcase、评测、面试展示和后续线上排障 |
| 饮食推荐 Agent | LLM 全链路 fallback | 意图识别失败走关键词；追问失败走模板；RAG 失败给保守回复；测算失败提示缺失字段 | MVP 即使模型异常也能返回可解释结果 |
| 饮食推荐 Agent | 输出层 RiskGuard | 新增 `PolicySafetyGuard`，检查绝对化承诺、法律结果保证、医疗/伤残等级确定性判断等高风险表达 | 工伤政务咨询必须强调“以经办机构和正式材料为准” |
| EchoMind | 三路融合意图识别 | MVP 采用简化版：LLM 意图 + 关键词规则；向量相似问题召回先作为 P1 | 当前 MVP 已有 RAG 重点，先不额外引入意图向量库 |
| EchoMind | 评测与监控闭环 | CLI 提供 `/eval <dataset>`，按 trace/badcase 数据计算 intent、slot、citation、calculation、fallback 指标 | 让项目从“能对话”变成“可评估、可迭代” |
| Pico | 控制面 / 状态面 / 证据面 | 控制面由 `AgentOrchestrator` 负责，状态面由 `SessionState` / `MemoryManager` 负责，证据面由 `TraceRecorder` / `EvalRunner` / `BadcaseStore` 负责 | 把系统从“Agent 调用集合”提升为可治理的 Agent Harness |
| Pico | Run artifacts | 每轮咨询生成 `TaskState`、`trace`、`report` 三类运行证据 | 支撑复盘、评测和 badcase 定位 |
| Pico | ContextManager 分段预算 | 上下文拆成系统规则、active slots、recent turns、RAG evidence、current query，并记录裁剪 metadata | 多轮政务咨询会膨胀，必须保证当前问题和政策依据优先保留 |
| Pico | ToolExecutor 统一工具边界 | RAG、待遇测算、地区过滤全部经过统一工具执行层 | 模型不能直接碰业务工具，否则 trace、评测和安全治理都不可信 |
| Pico | 分层评测 | 分别评估 intent、slot、RAG、citation、calculation、safety、answer | 失败时能定位是哪一层坏了，而不是只得到一个模糊总分 |

#### 4.4.2 MVP 暂不接入

| 设计 | 暂不接入原因 | 后续接入条件 |
|---|---|---|
| 自动 Agent 降权 | MVP 只有 4 个核心 Agent，且不是多个同职责 Agent 竞争，自动降权没有足够收益 | P2 引入多个模型或多个检索策略并行竞争后再做 |
| 三层记忆完整实现：Redis 工作记忆 + 向量情景记忆 + 用户画像 | CLI MVP 不需要 Redis；长期用户画像在政务咨询中也有隐私和合规成本 | FastAPI 服务化、多用户会话、真实线上日志接入后再做 |
| 复合问题并行调用多个 Worker | MVP 可以支持复合意图识别，但先串行编排，避免过早引入并发复杂度 | 出现“待遇测算 + 工伤认定 + 地方材料清单”这类高频复合问题后再并行 |
| 前端 Trace / 标注页面 | 用户已明确第一阶段无前端 CLI | API 版本或后台管理版本再建设 |
| PERSONAL / PUBLIC 双数据源模式 | 饮食项目中的个人库/公共库适合推荐业务；安安虎当前更像国家政策库 + 地方政策库 | 后续多地市上线时演进为 `national_policy` / `local_policy` / `case_library` 三类知识源 |
| Pico 的代码仓库上下文 | 安安虎不是代码仓库 Agent，不需要 repo、branch、dirty status、file fingerprint | 不接入 |
| Pico 的文件读写 / patch / shell 工具 | 工伤咨询不需要代码文件操作，接入会污染业务边界 | 不接入 |
| Pico 的 delegate 子 Agent | 会让 MVP 再次膨胀成很多 Agent，违背当前收敛原则 | 不接入 |
| 完整 checkpoint / resume 漂移识别 | Pico 防的是代码仓库变化；安安虎 MVP 只需要防地区、政策版本、关键槽位误继承 | 只做轻量 session 恢复 |
| MCP / Skill 扩展体系 | 属于平台化能力，当前阶段先把 RAG、测算、trace、badcase 做稳 | P2 之后再评估 |
| 复杂 prompt cache benchmark | 成本优化价值低于正确性、依据性和安全性 | 架构预留，不作为 MVP 目标 |

#### 4.4.3 对安安虎 MVP 的具体调整

结合上述参考项目，MVP 架构增加以下设计约束：

1. **Agent 无状态。** Agno Agent 不直接保存业务状态，所有上下文由 `AgentContext` 注入，最终状态由 `AgentOrchestrator` 写回。
2. **路由结果必须可修正。** `IntentRouterAgent` 的输出不是最终路由，必须经过规则层修正和置信度判断。
3. **槽位必须结构化。** 工伤咨询的地区、事故类型、时间、责任、伤情、材料状态、工资、缴费状态等字段必须有 schema，禁止只靠自然语言上下文传递。
4. **Trace 先于功能扩张。** 新增任何 Agent、Tool 或规则，都必须先定义 trace 事件，否则后续无法定位 badcase。
5. **Guard 是 MVP 必需能力。** 政务咨询输出必须经过保守性和依据完整性检查，避免输出“肯定认定工伤”“一定能赔多少钱”等绝对化结论。

## 5. 业务流程梳理

### 5.1 政府办事大厅咨询流程

```text
群众提出问题
  ↓
系统识别意图：工伤认定 / 劳动能力鉴定 / 参保认定 / 待遇测算 / 其他
  ↓
抽取地区、伤情、时间、事故场景、材料状态等关键信息
  ↓
判断问题是否信息不足
  ├── 不足：追问补充信息
  └── 足够：路由到对应专家 Agent
  ↓
专家 Agent 调用法规 RAG、测算工具或其他工具
  ↓
聚合结果，检查法规依据、地区一致性和风险提示
  ↓
返回：结论 + 依据 + 办事材料 + 下一步建议 + 风险提示
```

### 5.2 工伤认定咨询流程

典型问题：

```text
上班路上发生交通事故，能不能认定工伤？
```

流程：

```text
IntentRouterAgent
  ↓
识别为 work_injury_recognition
  ↓
抽取：事故类型、时间、地点、责任划分、地区
  ↓
DomainConsultationAgent（task_type=work_injury_recognition）
  ↓
PolicyRAGTool 检索《工伤保险条例》与地方政策
  ↓
AnswerValidator 检查法规依据和条件表达
  ↓
FinalAnswerAggregator 输出
```

### 5.3 劳动能力鉴定咨询流程

典型问题：

```text
劳动能力鉴定需要准备哪些材料？
```

流程：

```text
IntentRouterAgent
  ↓
DomainConsultationAgent（task_type=labor_capacity）
  ↓
PolicyRAGTool 检索鉴定标准、经办规程、地方办事指南
  ↓
输出材料清单、办理路径、注意事项
```

### 5.4 待遇测算流程

典型问题：

```text
四川 35 岁，伤残十级，大概能赔多少钱？
```

流程：

```text
IntentRouterAgent
  ↓
PaymentCalculationAgent
  ↓
抽取省份、年龄、性别、伤残等级、事故类型
  ↓
信息缺失则由 IntentRouterAgent / PaymentCalculationAgent 生成追问
  ↓
PaymentCalculationTool 结构化计算
  ↓
PolicyRAGTool 补充政策依据
  ↓
Aggregator 输出测算结果和免责声明
```

## 6. 数据流设计

### 6.1 在线请求数据流

```text
CLI 输入
  ↓
RequestContext
  - request_id
  - user_query
  - city / province
  - session_id
  ↓
IntentResult
  - intent
  - confidence
  - slots
  - is_composite
  - missing_slots
  ↓
IntentReviseRule
  - keyword_override
  - confidence_gate
  - composite_intent_policy
  ↓
SlotMergeResult
  - current_slots
  - active_slots
  - missing_slots
  ↓
AgentPlan
  - route_agents
  - required_tools
  - execution_mode
  ↓
ToolCallResults
  - retrieved_docs
  - calculation_result
  - external_result
  ↓
AgentOutputs
  - domain_answer
  - evidence
  - risk_notes
  ↓
VerifiedAnswer
  - final_answer
  - citations
  - confidence
  - warnings
  ↓
PolicySafetyGuard
  - citation_required
  - region_consistency
  - no_absolute_commitment
  ↓
TraceRecord / BadcaseRecord
```

### 6.2 知识库数据流

```text
data/documents/
  ↓
DocumentLoader
  ↓
DocumentChunker
  ↓
EmbeddingModel
  ↓
VectorStore
  ↓
Retriever
  ↓
Reranker
  ↓
PolicyRAGTool
```

### 6.3 评测数据流

```text
eval_cases.jsonl
  ↓
CLI eval runner
  ↓
AgentOrchestrator
  ↓
输出 answer + trace
  ↓
Rule-based checks + LLM-as-Judge
  ↓
metrics.json
  ↓
badcase.jsonl
```

### 6.4 Agent 间上下文传递数据流

不同 Agent 之间不直接传递自然语言长文本，而是通过统一 `AgentContext` 和结构化 `AgentMessage` 传递上下文。

```text
AgentContext
  ↓
IntentRouterAgent 写入 intent_result
  ↓
IntentReviseRule 修正 intent_result，SlotMergeRule 合并 active_slots
  ↓
AgentOrchestrator 根据修正后的 intent_result 写入 agent_plan
  ↓
DomainAgent 读取 intent_result / agent_plan / memory，写入 agent_outputs
  ↓
ToolExecutor 写入 tool_results
  ↓
ResultAggregator 读取 agent_outputs / tool_results，生成 draft_final_answer
  ↓
AnswerValidator 读取 draft_final_answer / agent_outputs / tool_results，写入 verification_result
  ↓
PolicySafetyGuard 读取 draft_final_answer / citations / warnings，写入 safety_result
  ↓
ResultAggregator 根据 verification_result / safety_result 生成 final_answer
```

这种设计有 3 个目的：

- **可追踪：** 每个 Agent 读了什么、写了什么，都可以进入 trace。
- **可测试：** 单个 Agent 可以用固定 `AgentContext` 做单元测试。
- **可替换：** 后续替换模型或 Agent 实现，不影响上下文协议。

## 7. 总体架构设计

```text
CLI
  ↓
AgentOrchestrator
  ├── IntentRouterAgent
  ├── IntentReviseRule
  ├── SlotMergeRule
  ├── ContextManager
  ├── AgentRegistry
  ├── MemoryManager
  ├── ToolExecutor
  ├── ResultAggregator
  ├── AnswerValidator
  ├── PolicySafetyGuard
  └── TraceRecorder
       ↓
MVP Agents
  ├── DomainConsultationAgent
  ├── PaymentCalculationAgent
  └── PolicyRAGAgent
       ↓
Tools
  ├── PolicyRAGTool
  ├── PaymentCalculationTool
  ├── RegionPolicyFilterTool
  └── CitationFormatterTool
       ↓
Infrastructure
  ├── ModelRouter
  ├── VectorStore
  ├── MemoryStore
  ├── TaskStateStore
  ├── TraceStore
  ├── ReportStore
  └── EvalStore
```

这套架构参考 Pico 的 Agent Harness 思路，但只吸收运行时治理能力，不吸收代码 Agent 的文件操作能力：

| 面 | MVP 组件 | 作用 |
|---|---|---|
| 控制面 | `AgentOrchestrator`、`ContextManager`、`ToolExecutor`、`ModelRouter` | 决定一轮咨询怎么推进、怎么调用模型和工具 |
| 状态面 | `SessionState`、`MemoryManager`、`TaskStateStore` | 保存当前会话、槽位、路由、工具状态和轻量恢复信息 |
| 证据面 | `TraceRecorder`、`ReportStore`、`EvalStore`、`BadcaseStore` | 保存可回放、可评测、可对比的运行证据 |
| 治理面 | `AnswerValidator`、`PolicySafetyGuard`、fallback 规则 | 控制引用依据、地区一致性、政务安全和降级策略 |

## 8. Agent 设计

### 8.1 Agent 设计原则

1. 按业务职责拆分，而不是按技术名词拆分。
2. 每个 Agent 必须有明确输入、输出和可评测指标。
3. 简单任务用轻量模型，复杂推理用强模型。
4. 工具调用必须可记录、可回放、可评测。
5. Agent 输出必须结构化，便于聚合和校验。
6. MVP 只保留职责差异明确的 Agent，不为了「多 Agent」而拆 Agent。

### 8.2 MVP Agent 清单

MVP 只实现 4 个核心 Agent。其他能力不进入 MVP Agent 清单，避免把“未来可能拆分的能力”误读为当前必须实现的 Agent。

| Agent | 职责 | 模型建议 | P0/P1 |
|---|---|---|---|
| `IntentRouterAgent` | 意图识别、槽位抽取、置信度判断 | 轻量快速模型 + 规则兜底 | P0 |
| `PolicyRAGAgent` | 法规检索、引用依据组织 | 中等模型或无模型工具型 Agent | P0 |
| `DomainConsultationAgent` | 工伤认定、劳动能力鉴定、参保认定等文本政策咨询 | 中等模型，复杂问题可升级强推理模型 | P0 |
| `PaymentCalculationAgent` | 待遇测算解释和工具调用 | 中等模型 + 计算工具 | P0 |

### 8.3 MVP 路由策略

```text
用户问题
  ↓
IntentRouterAgent
  ├── policy_consultation / work_injury_recognition / labor_capacity / insurance_participation
  │       ↓
  │   DomainConsultationAgent
  │       ↓
  │   PolicyRAGAgent
  │
  └── payment_calculation
          ↓
      PaymentCalculationAgent
          ↓
      PolicyRAGAgent（补充依据）
```

如果 `IntentRouterAgent` 判断置信度低于阈值，MVP 不进入复杂多 Agent 协作，而是直接生成追问。

MVP 路由不直接采用 LLM 原始输出，而是采用三段式决策：

```text
IntentRouterAgent 原始识别
  ↓
IntentReviseRule 规则修正
  ↓
AgentOrchestrator 生成最终 AgentPlan
```

`IntentReviseRule` 至少包含以下规则：

| 规则 | 条件 | 处理 |
|---|---|---|
| 低置信度追问 | `confidence < 0.6` 且缺少关键槽位 | 不进入业务 Agent，返回追问 |
| 待遇测算强命中 | 用户输入包含“赔多少钱 / 待遇 / 一次性伤残补助金 / 医疗补助金”等 | 优先修正为 `payment_calculation` |
| 认定咨询强命中 | 用户输入包含“算不算工伤 / 能不能认定 / 上下班途中 / 非本人主要责任”等 | 优先修正为 `work_injury_recognition` |
| 鉴定咨询强命中 | 用户输入包含“劳动能力鉴定 / 伤残等级 / 鉴定材料 / 复查鉴定”等 | 优先修正为 `labor_capacity` |
| 地区继承保护 | 当前轮未提供地区，但历史会话有地区 | 可以继承，但 trace 中标记 `region_inherited=true` |
| 地区冲突保护 | 当前轮地区与历史地区冲突 | 以当前轮为准，并记录 `region_overridden=true` |

复合意图在 MVP 阶段只做识别和串行处理，不做并行调度。例如“我在丹东上班受伤，能不能认定工伤，十级能赔多少钱”会被拆成：

```text
DomainConsultationAgent -> PolicyRAGAgent -> PaymentCalculationAgent -> ResultAggregator
```

后续如果复合问题占比高，再升级为并行 Team / Workflow。

## 9. Agent 间上下文传递设计

### 9.1 核心原则

Agent 之间不共享可变全局变量，也不互相直接调用内部方法。所有协作都通过 `AgentContext` 传递。

每个 Agent 的执行边界：

```text
读取 AgentContext
  ↓
执行本 Agent 决策 / 工具调用 / 生成
  ↓
返回 AgentMessage 或 AgentResult
  ↓
由 AgentOrchestrator 合并回 AgentContext
```

`AgentOrchestrator` 是唯一允许合并上下文的组件。

### 9.2 `AgentContext` 格式

```json
{
  "request": {
    "request_id": "req_20260708_0001",
    "session_id": "sess_001",
    "turn_id": 1,
    "user_query": "四川 35 岁，伤残十级，大概能赔多少钱？",
    "input_type": "text",
    "province": "四川省",
    "city": "成都市",
    "created_at": "2026-07-08T21:30:00+08:00"
  },
  "conversation": {
    "history_summary": "用户正在咨询工伤待遇测算。",
    "last_user_intent": "payment_calculation",
    "last_answer_summary": "",
    "active_slots": {
      "province": "四川省",
      "city": "成都市"
    }
  },
  "intent_result": {
    "intent": "payment_calculation",
    "confidence": 0.89,
    "is_composite": false,
    "slots": {
      "age": 35,
      "injury_level": "十级",
      "province": "四川省"
    },
    "missing_slots": ["gender"]
  },
  "agent_plan": {
    "route_agents": [
      "PaymentCalculationAgent",
      "PolicyRAGAgent"
    ],
    "execution_mode": "sequential",
    "reason": "需要先计算待遇，再补充政策依据。"
  },
  "tool_results": [],
  "agent_outputs": [],
  "draft_final_answer": null,
  "verification_result": null,
  "safety_result": null,
  "final_answer": null,
  "trace": {
    "events": [],
    "latency_ms": 0,
    "status": "running"
  }
}
```

### 9.2.1 工伤业务槽位 schema

MVP 需要把关键业务信息显式结构化，避免 Agent 之间只靠自然语言摘要传递。槽位分为通用槽位、工伤认定槽位、劳动能力鉴定槽位和待遇测算槽位。

| 槽位 | 类型 | 适用任务 | 说明 |
|---|---|---|---|
| `province` | string | 全部 | 省份，用于政策过滤 |
| `city` | string | 全部 | 地市，用于合作地区和地方政策匹配 |
| `accident_time` | string/date | 工伤认定 | 事故发生时间 |
| `accident_scene` | enum | 工伤认定 | 工作时间、工作场所、上下班途中、外出工作等 |
| `traffic_responsibility` | enum | 工伤认定 | 本人主要责任、非本人主要责任、责任不明 |
| `employment_status` | enum | 工伤认定 / 参保认定 | 劳动关系、劳务关系、灵活就业、未知 |
| `insured_status` | enum | 参保认定 / 待遇测算 | 已参保、未参保、不确定 |
| `injury_level` | enum | 劳动能力鉴定 / 待遇测算 | 一级至十级、未鉴定、不确定 |
| `medical_status` | enum | 劳动能力鉴定 | 治疗中、停工留薪期、已出院、病情稳定 |
| `average_wage` | number | 待遇测算 | 本人工资或缴费工资 |
| `age` | int | 待遇测算 | 年龄，影响部分长期待遇估算 |
| `gender` | enum | 待遇测算 | 男、女、未知 |
| `terminate_labor_relation` | bool | 待遇测算 | 是否解除或终止劳动关系 |
| `materials_status` | array | 办事指南 | 已有材料，例如诊断证明、劳动合同、事故证明 |

槽位合并规则：

| 规则 | 说明 |
|---|---|
| 当前轮非空优先 | 当前轮明确提供的槽位覆盖历史槽位 |
| 当前轮为空保留历史 | 用户只补充一个字段时，不清空其他已知字段 |
| 地区字段显式记录来源 | 继承历史地区时标记 `source=history`，当前轮提供时标记 `source=current_turn` |
| 高风险字段不盲目继承 | `injury_level`、`average_wage`、`traffic_responsibility` 等影响结论的字段，跨主题时需要重新确认 |
| 非法枚举丢弃并追问 | LLM 输出不在枚举范围内时，不写入上下文，改为 `missing_slots` |

### 9.3 `AgentMessage` 格式

每个 Agent 返回结构化消息，不直接返回最终长答案。

```json
{
  "agent_name": "PaymentCalculationAgent",
  "message_type": "domain_result",
  "confidence": 0.82,
  "content": {
    "summary": "已根据四川省、35 岁、十级伤残进行待遇测算，但缺少性别字段，使用平均退休年龄作为临时估算。",
    "structured_result": {
      "medical_aid": 12345.67,
      "disability_aid": 23456.78,
      "total": 35802.45
    },
    "assumptions": [
      "未提供性别，暂按平均退休年龄估算。"
    ],
    "warnings": [
      "测算结果仅供咨询参考，最终以经办机构核定为准。"
    ]
  },
  "evidence": [
    {
      "source_type": "tool",
      "source_name": "PaymentCalculationTool",
      "ref_id": "tool_call_001"
    }
  ],
  "next_actions": [
    {
      "type": "clarify",
      "field": "gender",
      "question": "请问伤者性别是男还是女？这会影响部分长期待遇测算。"
    }
  ]
}
```

### 9.4 `ToolCallResult` 格式

```json
{
  "tool_call_id": "tool_call_001",
  "tool_name": "PolicyRAGTool",
  "called_by": "PolicyRAGAgent",
  "input": {
    "query": "四川 十级伤残 工伤待遇",
    "province": "四川省",
    "city": "成都市",
    "top_k": 5
  },
  "output": {
    "documents": [
      {
        "title": "四川省工伤保险条例实施办法",
        "content": "……",
        "score": 0.82,
        "province": "四川省",
        "city": ""
      }
    ]
  },
  "success": true,
  "latency_ms": 320,
  "error": null
}
```

### 9.5 上下文读写权限

为了控制上下文污染，Agent 只能读取自己需要的字段：

| Agent | 允许读取 | 允许写入 |
|---|---|---|
| `IntentRouterAgent` | `request`、`conversation` | `intent_result` |
| `AgentOrchestrator` | `request`、`intent_result` | `agent_plan` |
| `PolicyRAGAgent` | `request`、`intent_result`、`agent_plan` | `tool_results`、`agent_outputs` |
| `DomainConsultationAgent` | `request`、`intent_result`、`agent_plan`、`tool_results` | `agent_outputs` |
| `PaymentCalculationAgent` | `request`、`intent_result` | `tool_results`、`agent_outputs` |
| `AnswerValidator` | `draft_final_answer`、`agent_outputs`、`tool_results`、`intent_result` | `verification_result` |
| `PolicySafetyGuard` | `draft_final_answer`、`verification_result`、`request`、`intent_result` | `safety_result` |
| `ResultAggregator` | 全部只读 | `draft_final_answer`、`final_answer` |

## 10. 多模型适配设计

### 10.1 为什么需要多模型

不同 Agent 的任务复杂度不同：

- 意图识别、追问生成：要求快、便宜、稳定。
- 法规推理、冲突检查：要求强推理、可靠性高。
- 待遇测算：核心是结构化计算，不应依赖大模型算数。
- 隐患识别：需要多模态模型。
- 评测 Judge：需要相对强且稳定的模型。

### 10.2 ModelRouter

设计一个统一 `ModelRouter`，根据 Agent 类型和任务复杂度选择模型。

```text
Agent 请求模型
  ↓
ModelRouter
  ├── intent_fast_model
  ├── domain_reasoning_model
  ├── verifier_reasoning_model
  └── judge_model
  ↓
Agno Model Provider
```

### 10.3 模型配置示例

```yaml
models:
  intent_fast:
    provider: openai_compatible
    model: qwen-turbo
    temperature: 0

  domain_reasoning:
    provider: openai_compatible
    model: deepseek-r1
    temperature: 0.2

  verifier:
    provider: openai_compatible
    model: qwen-max
    temperature: 0

  judge:
    provider: openai_compatible
    model: gpt-4.1
    temperature: 0

```

多模态模型不进入 MVP 配置。语音和图片能力属于 P1 输入通道，等文本链路稳定后再加入。

### 10.4 模型选择策略

| 场景 | 策略 |
|---|---|
| 简单分类 | 轻量模型 |
| 法规推理 | 强推理模型 |
| 结构化计算 | 工具计算，模型只解释 |
| 多模态识别 | 多模态模型 |
| 低置信度 | 升级到强模型或追问 |
| Agent 结果冲突 | Verifier 使用强模型复核 |

## 11. 记忆系统设计

第一版 CLI 也要保留记忆接口，但可以轻实现。

| 记忆类型 | 内容 | 第一版实现 |
|---|---|---|
| 工作记忆 | 当前请求的意图、槽位、工具结果 | 内存对象 |
| 会话记忆 | 多轮对话摘要、地区、历史问题 | SQLite / JSONL |
| 用户画像 | 常用地区、常问业务类型 | P1 |
| Badcase 记忆 | 失败问题、失败原因、修正答案 | JSONL |

### 11.1 上下文管理设计

MVP 引入轻量 `ContextManager`，参考 Pico 的分段上下文预算思想，但不做复杂长期记忆。它的职责是把当前轮 Agent 输入拆成可解释的上下文段，并在超预算时按优先级裁剪。

上下文分段：

| Section | 内容 | 裁剪优先级 |
|---|---|---|
| `system_prefix` | Agent 身份、输出协议、安全边界、工具说明 | 最后裁剪 |
| `active_slots` | 当前会话已确认的地区、事故场景、伤残等级、工资等槽位 | 尽量保留 |
| `rag_evidence` | 本轮检索到的法规、地方政策、办事指南 | 尽量保留 |
| `recent_turns` | 最近 3-5 轮对话摘要 | 可压缩 |
| `working_memory` | 上轮结论、待追问字段、工具失败摘要 | 可压缩 |
| `current_query` | 用户当前问题 | 不裁剪 |

默认裁剪顺序：

```text
recent_turns -> working_memory -> rag_evidence 摘要化 -> active_slots 摘要化 -> system_prefix
```

`current_query` 不允许裁剪。每次构建上下文都要写入 metadata：

```json
{
  "prompt_chars": 8420,
  "sections": {
    "system_prefix": 1200,
    "active_slots": 900,
    "rag_evidence": 4200,
    "recent_turns": 1400,
    "working_memory": 500,
    "current_query": 220
  },
  "trimmed_sections": ["recent_turns"],
  "current_query_preserved": true
}
```

## 12. 工具设计

### 12.1 Tool 清单

| Tool | 职责 | 来源 |
|---|---|---|
| `PolicyRAGTool` | 检索法规、地方政策、办事指南 | 原 RAG 模块 |
| `PaymentCalculationTool` | 工伤待遇测算 | 原待遇测算服务 |
| `RegionPolicyFilterTool` | 根据省市过滤政策 | 原 RAG 地区过滤逻辑 |
| `CitationFormatterTool` | 格式化引用依据 | 新增 |
| `TraceTool` | 写入调用链 trace | 新增 |
| `BadcaseTool` | 记录失败案例 | 新增 |

`HazardImageTool`、`SpeechRecognitionTool`、`WebSearchTool` 不进入 MVP Tool 清单。它们属于 P1 / P2 输入通道或外部增强能力，避免第一版 CLI 变成多模态平台。

### 12.2 Tool 调用规范

所有工具必须通过 `ToolExecutor` 调用，Agent 不允许直接调用底层 RAG、测算或存储函数。

每次工具调用必须记录：

- tool_name
- input
- output
- latency_ms
- success
- error_message
- related_agent
- request_id

`ToolExecutor` 统一处理：

| 能力 | 说明 |
|---|---|
| 工具注册校验 | 只允许调用已注册工具 |
| 参数 schema 校验 | 省市、伤残等级、工资、top_k 等参数必须符合结构 |
| 超时控制 | 防止 RAG、模型或外部接口阻塞 CLI |
| 重复调用拦截 | 同一轮中连续相同工具调用需要记录并限制 |
| 错误码归一 | 将底层异常转成 `tool_error_code` |
| fallback 标记 | 工具失败后写入 `fallback_used` 和 `fallback_reason` |
| trace 事件 | 每次调用写入 `tool_called` / `tool_finished` / `tool_failed` |

工具调用返回结构必须包含：

```json
{
  "tool_name": "PolicyRAGTool",
  "tool_status": "success",
  "tool_error_code": null,
  "latency_ms": 320,
  "input": {},
  "output": {},
  "fallback_used": false
}
```

## 13. 结果聚合与校验设计

多 Agent 输出不能直接拼接，必须通过聚合和校验。

### 13.1 聚合流程

```text
AgentOutputs
  ↓
去重
  ↓
按业务结构组织
  ↓
引用依据检查
  ↓
地区一致性检查
  ↓
冲突检测
  ↓
PolicySafetyGuard 政务安全检查
  ↓
敏感提示和免责声明
  ↓
FinalAnswer
```

### 13.2 输出结构

```text
1. 简短结论
2. 判断依据
3. 适用条件
4. 办事材料或下一步建议
5. 风险提示
6. 引用来源
```

### 13.3 `PolicySafetyGuard` 规则

`PolicySafetyGuard` 是 MVP 必需的输出治理函数，不作为独立 Agent。它的目标是让政务咨询回答保持“可解释、可追溯、不过度承诺”。

| 规则 | 检查内容 | 处理方式 |
|---|---|---|
| 禁止绝对化结论 | “一定能认定”“肯定赔付”“保证通过”等 | 改写为条件化表达 |
| 必须提示经办口径 | 涉及认定、鉴定、待遇核定 | 增加“最终以经办机构核定为准” |
| 引用依据必需 | 政策咨询类回答没有 citations | 标记为候选 badcase，返回保守回答 |
| 地区一致性 | 用户指定地区与引用政策地区不一致 | 降低置信度，提示需要核对当地政策 |
| 医疗/等级边界 | 直接判断伤残等级或替代医学鉴定 | 改为建议走劳动能力鉴定流程 |
| 金额测算边界 | 待遇测算缺少关键字段却输出精确金额 | 改为区间估算或追问缺失字段 |

Guard 输出写入 `safety_result`：

```json
{
  "passed": false,
  "risk_level": "medium",
  "reasons": ["missing_citation", "absolute_commitment"],
  "rewrite_required": true,
  "suggested_warning": "以上仅供办事咨询参考，最终以当地经办机构核定为准。"
}
```

## 14. 交互式 CLI 版本设计

### 14.1 CLI 交互模式

MVP 的核心入口是交互式启动，而不是一次性命令。用户运行：

```bash
python -m ananhu_agent
```

进入交互式 CLI：

```text
安安虎工伤智能助手 Agno MVP
当前模式：交互式咨询
输入 /help 查看命令，输入 /exit 退出。

>
```

支持内置命令：

| 命令 | 说明 |
|---|---|
| `/help` | 查看可用命令 |
| `/new` | 开启新会话 |
| `/context` | 查看当前会话上下文摘要 |
| `/trace` | 查看最近一次请求的 trace |
| `/badcase` | 将最近一次回答标记为 badcase |
| `/feedback good` | 标记最近一次回答有效 |
| `/feedback bad` | 标记最近一次回答无效，并进入 badcase 收集流程 |
| `/eval <dataset>` | 运行离线评测 |
| `/exit` | 退出 CLI |

仍保留非交互式命令，便于自动化测试：

```bash
python -m ananhu_agent ask "上班路上交通事故算工伤吗？" --province 四川省 --city 成都市
python -m ananhu_agent eval --dataset eval_cases.jsonl
python -m ananhu_agent trace show <request_id>
```

### 14.2 交互式会话流程

```text
启动 CLI
  ↓
创建 session_id
  ↓
用户输入问题
  ↓
AgentOrchestrator 处理
  ↓
展示意图、路由、工具调用摘要、最终回答
  ↓
等待用户下一步输入
  ├── 输入新问题：继续当前会话
  ├── /feedback good：记录正反馈
  ├── /feedback bad：进入 badcase 收集
  ├── /trace：查看 trace
  └── /exit：退出
```

### 14.3 CLI 输出示例

```text
> 上班路上发生交通事故，能认定工伤吗？

[Intent]
- intent: work_injury_recognition
- confidence: 0.91
- route: DomainConsultationAgent + PolicyRAGAgent

[Tools]
- PolicyRAGTool: success, top_k=5

[Answer]
简短结论：
如果是在合理上下班路线和合理时间内发生非本人主要责任的交通事故，通常具备认定工伤的条件。

判断依据：
……

下一步建议：
……

[Trace]
request_id: req_20260708_xxx
latency: 4.2s
```

### 14.4 badcase 交互式收集流程

当用户输入 `/badcase` 或 `/feedback bad` 时，CLI 不只记录「差评」，还要引导用户补充结构化信息：

```text
你要把最近一次回答标记为 badcase。

请选择问题类型：
1. 意图识别错误
2. 法规检索不准
3. 回答有幻觉
4. 地区政策不匹配
5. 工具调用失败
6. 回答不完整
7. 其他

请输入编号：
```

继续收集：

```text
请补充你认为正确的答案或修正方向（可跳过）：
请补充备注（可跳过）：
是否加入回归评测集？[y/N]
```

系统写入 `badcases.jsonl`，并关联最近一次 `request_id`。

## 15. 数据模型设计

第一版不必引入复杂数据库，可以 SQLite + JSONL 起步。

MVP 采用三类运行证据：

| 类型 | 作用 | 形式 |
|---|---|---|
| `task_states` | 当前轮运行快照，回答“这轮跑到哪一步” | SQLite 表或 JSON |
| `agent_traces` | 逐事件时间线，回答“中间发生了什么” | SQLite 表或 JSONL |
| `run_reports` | 运行摘要，回答“最后拿什么做统计” | SQLite 表或 JSON |

### 15.1 `task_states`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | request_id |
| session_id | string | 会话 ID |
| turn_id | int | 当前轮次 |
| user_query | text | 用户输入 |
| status | string | running / success / failed / clarified |
| current_phase | string | intent / route / tool / aggregate / validate / final |
| raw_intent | string | LLM 原始意图 |
| revised_intent | string | 规则修正后的意图 |
| active_slots | json | 当前有效槽位 |
| missing_slots | json | 缺失槽位 |
| route_agents | json | 本轮计划调用的 Agent |
| tool_steps | int | 已执行工具次数 |
| model_attempts | int | 模型调用或重试次数 |
| fallback_used | bool | 是否触发降级 |
| error_message | text | 失败摘要 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 15.2 `agent_traces`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | trace event ID |
| request_id | string | 关联 `task_states.id` |
| session_id | string | 会话 ID |
| event_type | string | intent_recognized / tool_called / answer_validated 等 |
| phase | string | intent / route / tool / aggregate / validate / final |
| payload | json | 事件输入输出 |
| latency_ms | int | 当前事件耗时 |
| created_at | datetime | 创建时间 |

事件 payload 中至少保留以下聚合字段，便于查询：

| 字段 | 类型 | 说明 |
|---|---|---|
| user_query | text | 用户输入 |
| province | string | 省份 |
| city | string | 城市 |
| intent | string | 识别意图 |
| raw_intent | string | LLM 原始意图 |
| revised_intent | string | 规则修正后的意图 |
| confidence | float | 置信度 |
| active_slots | json | 合并后的业务槽位 |
| missing_slots | json | 缺失槽位 |
| route_agents | json | 被调用 Agent |
| tool_calls | json | 工具调用记录 |
| draft_answer | text | 安全检查前的答案草稿 |
| verification_result | json | 引用、地区、冲突等校验结果 |
| safety_result | json | `PolicySafetyGuard` 检查结果 |
| final_answer | text | 最终回答 |
| fallback_used | bool | 是否触发降级 |
| fallback_reason | string | 降级原因 |
| latency_ms | int | 总耗时 |
| status | string | success / failed / clarified |
| created_at | datetime | 创建时间 |

### 15.3 `run_reports`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | request_id |
| session_id | string | 会话 ID |
| final_status | string | success / failed / clarified |
| final_intent | string | 最终意图 |
| route_agents | json | 实际调用 Agent |
| tool_count | int | 工具调用次数 |
| model_attempts | int | 模型调用或重试次数 |
| prompt_metadata | json | ContextManager 输出的上下文分段和裁剪信息 |
| token_usage | json | token 或字符统计 |
| latency_ms | int | 总耗时 |
| fallback_used | bool | 是否触发降级 |
| safety_result | json | 安全检查摘要 |
| badcase_candidate | bool | 是否候选 badcase |
| created_at | datetime | 创建时间 |

### 15.4 `badcases`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | badcase ID |
| request_id | string | 关联 trace |
| query | text | 原始问题 |
| predicted_intent | string | 预测意图 |
| issue_type | string | intent_error / rag_miss / hallucination / tool_error |
| expected_answer | text | 人工修正答案 |
| fixed | bool | 是否已修复 |
| created_at | datetime | 创建时间 |

建议增加字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| session_id | string | 会话 ID |
| turn_id | int | 当前轮次 |
| agent_route | json | 实际调用的 Agent |
| tool_calls | json | 工具调用快照 |
| actual_answer | text | 系统原始回答 |
| correction_note | text | 用户补充的修正方向 |
| added_to_eval | bool | 是否加入回归评测集 |

### 15.5 `eval_cases`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | string | 用例 ID |
| query | text | 测试问题 |
| province | string | 省份 |
| city | string | 城市 |
| expected_intent | string | 期望意图 |
| expected_keywords | json | 期望命中关键词 |
| expected_citations | json | 期望法规来源 |
| difficulty | string | easy / medium / hard |

## 16. badcase 收集与回流设计

### 16.1 badcase 来源

badcase 不只来自用户差评。MVP 阶段设计 4 个来源：

| 来源 | 触发方式 | 说明 |
|---|---|---|
| 用户主动标记 | CLI `/badcase` | 用户认为最近一次回答有问题 |
| 负反馈 | CLI `/feedback bad` | 用户快速差评后进入结构化收集 |
| 系统自动标记 | 低置信度、工具失败、无引用依据 | 即使用户不反馈，也记录可疑案例 |
| 评测失败 | `eval` runner 指标不达标 | 自动写入回归 badcase |

### 16.2 自动 badcase 判定规则

满足任一条件，系统应自动记录为候选 badcase：

- `intent_result.confidence < 0.6`
- `PolicyRAGTool` 无检索结果。
- `AnswerValidator` 判定缺少法规依据。
- 用户问题包含明确地区，但最终答案未体现地区。
- 任一 P0 工具调用失败。
- 最终答案为空、过短或只给泛化建议。
- LLM-as-Judge 分数低于阈值。

### 16.3 badcase 生命周期

```text
候选 badcase
  ↓
人工或用户补充修正方向
  ↓
加入 badcases.jsonl
  ↓
必要时转成 eval_cases.jsonl
  ↓
修复 Agent / Prompt / Tool / RAG 数据
  ↓
运行回归评测
  ↓
标记 fixed=true
```

### 16.4 badcase JSONL 示例

```json
{
  "id": "bad_20260708_0001",
  "request_id": "req_20260708_0001",
  "session_id": "sess_001",
  "turn_id": 3,
  "query": "我在丹东上班受伤，待遇怎么算？",
  "predicted_intent": "payment_calculation",
  "issue_type": "region_policy_mismatch",
  "agent_route": ["PaymentCalculationAgent", "PolicyRAGAgent"],
  "tool_calls": ["tool_call_001", "tool_call_002"],
  "actual_answer": "按照四川省标准……",
  "expected_answer": "应优先匹配辽宁丹东或辽宁省政策。",
  "correction_note": "地区槽位被错误继承为四川省。",
  "added_to_eval": true,
  "fixed": false,
  "created_at": "2026-07-08T22:00:00+08:00"
}
```

## 17. 评测体系设计

### 17.1 第一版评测指标

| 指标 | 说明 |
|---|---|
| Intent Accuracy | 意图识别准确率 |
| Slot Accuracy | 地区、伤残等级、事故类型等槽位抽取准确率 |
| RAG Hit Rate | 期望法规是否进入 TopK |
| Citation Accuracy | 引用依据是否正确 |
| Tool Success Rate | 工具调用成功率 |
| Answer Pass Rate | LLM-as-Judge 或人工判定通过率 |
| Latency P50 / P95 | 响应耗时 |

### 17.2 最小评测集

第一版至少准备 30 条：

- 工伤认定：10 条。
- 劳动能力鉴定：8 条。
- 待遇测算：8 条。
- 复合问题：4 条。

## 18. 技术栈

| 层级 | 技术 | 选择理由 |
|---|---|---|
| Agent 框架 | Agno | 支持 Agent、Team、Workflow、Tools、Memory、Storage，适合多 Agent 系统 |
| CLI | Typer 或 argparse | 快速实现无前端交互 |
| 配置 | Pydantic Settings + YAML | 管理多模型、多环境配置 |
| LLM Provider | OpenAI-compatible、DashScope、DeepSeek 等 | 适配不同 Agent 的模型需求 |
| 异步策略 | async I/O 可用，不做后台任务架构 | 模型、RAG、存储可异步调用，但 CLI MVP 保持单轮同步主流程 |
| RAG | Milvus / Chroma（二选一） | 复用原项目 Milvus 经验；本地 MVP 可先用 Chroma 降低成本 |
| Embedding | DashScope Embedding | 复用原项目经验 |
| Reranker | BGE Reranker | 复用原项目经验 |
| 存储 | SQLite + JSONL | CLI MVP 简单可靠 |
| 日志 | loguru / structlog | 结构化日志 |
| 评测 | pytest + JSONL + LLM-as-Judge | 支持离线回归 |
| 包管理 | uv 或 Poetry | Python 项目依赖管理 |

## 19. 风险与取舍

### 19.1 风险

- Agno 框架能力足够，但团队需要熟悉它的 Agent、Team、Workflow、Storage 和 Tool 设计方式。
- 如果一开始就做 Web API、前端、语音、图片，会导致第一阶段失控。
- 多模型会增加配置复杂度，需要统一 ModelRouter。
- 评测集如果不补，项目仍然难以证明效果。
- 如果过早引入复杂异步调度、并行 Agent 或后台任务，会增加 trace 乱序、状态合并和 badcase 复现难度。

### 19.2 取舍

- 第一版优先 CLI，不做前端。
- 第一版优先文本咨询，不做语音和图片。
- 第一版优先 SQLite / JSONL，不上复杂数据库。
- 第一版保留 Milvus 方案，但允许本地 MVP 用 Chroma 降低启动成本。
- 第一版重点证明 Agent 闭环，而不是复刻线上所有能力。
- 第一版允许 async I/O，但不做复杂异步任务平台；流式输出只作为后续体验增强，不作为 MVP 核心目标。
- 第一版参考 Pico 的 Harness 思路，但不接入代码仓库工具、delegate、MCP / Skill 和完整 checkpoint / resume。

## 20. 参考资料

- Agno 官方文档：https://docs.agno.com/
- Agno Agent 文档：https://docs.agno.com/concepts/agents
- Agno Teams 文档：https://docs.agno.com/concepts/teams
- Agno Models 文档：https://docs.agno.com/concepts/models
- Agno Tools 文档：https://docs.agno.com/concepts/tools
- Agno Storage 文档：https://docs.agno.com/concepts/storage
- Agno Metrics 文档：https://docs.agno.com/concepts/metrics
- 原项目：`ananhu_common-main`
- 参考标准：`面试官认可的多agent项目.md`
- 参考项目：`饮食推荐Agent/Diet-Agent[1]`
- 参考项目：`EchoMind面试型多agent项目`
- 参考项目：`pico/pico.md`
