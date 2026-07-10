# 框架中立 LangGraph 演进计划

> **面向 AI 代理的工作者：** 使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 逐任务执行。每个任务必须从 `mvp` 创建独立分支，完成后等待用户确认，再提交并合并。

**目标：** 保持当前 Native MVP 可回归，先建立项目自己的业务阶段、状态、能力、trace 和运行时协议，再将 LangGraph 接入为默认且可替换的工作流运行时。

**架构：** Native 与 LangGraph Runtime 实现同一 `WorkflowRuntime`，使用同一阶段服务、reducer、CapabilityGateway、contract tests、eval cases 和 TraceEvent。LangGraph 类型只存在于 `runtimes/langgraph/` 和组合根。

**技术栈：** Python 3.11、uv、Pydantic、pytest、Typer；LangGraph 只在任务 30 引入。

---

## 0. 第一性原理

稳定资产是案件事实、jurisdiction、证据、状态转换、能力治理、Prompt、Trace、Usage 和 Eval。LangGraph、模型供应商、向量库、checkpointer 和观测产品都是可替换实现。

当前不做 HTTP、WebSocket、前端、复杂并行、开放式 planner 和生产 checkpoint。Checkpoint 只有在出现明确暂停恢复需求后才单独立项，不是本计划前置依赖。

## 1. 依赖图

```text
25 文档事实源
 -> 26 业务阶段与核心状态协议
 -> 27 StatePatch + Reducer + 调用身份 + Trace 协议
 -> 28 CapabilityGateway 端口与 ToolExecutor 适配
 -> 29 Native Runtime 阶段化与 Runtime Contract
 -> 30 最小 LangGraph Runtime
 -> 31 双运行时差分验收
      +-> 32 真实 ModelGateway
      +-> 33 真实 KnowledgeGateway
32 + 33 -> 34 真实咨询 Smoke Eval
```

无循环、无后置任务被前置使用。Checkpoint 恢复是计划外条件任务。

## 2. 任务清单

### 任务 25：统一 MVP 架构和计划事实源

**目标：** 消除 Agno 主路线、未实现代码、四 Agent 永久固定和 Orchestrator 永久唯一推进方等旧描述。

**涉及模块：** `AGENTS.md`、README、`TECH_ARCHITECTURE_MVP.md`、架构/API/后端规范、历史计划、changelog。

**前置依赖：** 任务 1-24 已完成。

**步骤流程：** 扫描旧口径；更新事实源；归档旧计划；建立本计划；运行术语扫描和全量测试。

**验证命令：**

```bash
rg -n -i "基于 Agno|尚未实现业务代码|尚未创建 Python 包|只保留 4 个核心 Agent" AGENTS.md README.md TECH_ARCHITECTURE_MVP.md docs/architecture.md docs/api-contracts.md docs/backend-conventions.md docs/architecture
uv run pytest -v
```

**验收标准：** 旧扫描无有效命中；当前与目标运行时边界一致；旧 Agno 待办不存在；53 项现有测试通过。

### 任务 26：锁定业务阶段并定义核心状态协议

**目标：** 先从当前行为提取稳定阶段，再定义不依赖框架的请求、状态和结果，避免枚举反向修改。

**涉及模块：** workflow contracts、characterization tests、旧 `AgentContext` mapper。

**前置依赖：** 任务 25。

**步骤流程：**

1. 为完成、追问、证据不足、能力失败和安全拦截建立 characterization tests。
2. 从测试确认 `understand -> merge_facts -> validate_facts -> clarify/resolve_jurisdiction -> plan -> execute -> validate_evidence -> compose -> safety -> complete`。
3. 定义 `RunRequest`、`WorkflowState`、`WorkflowResult`、`WorkflowPhase`、`RunStatus` 和 `StopReason`。
4. 定义 request/run/session/case/message 标识关系和 `schema_version`。
5. 测试 JSON round-trip 和旧 `AgentContext` 显式映射，暂不改变运行行为。

**验证命令：** `uv run pytest tests/test_workflow_contracts.py tests/test_orchestrator_characterization.py -v`

**验收标准：** 协议不导入任何 Agent 框架类型；阶段覆盖所有 characterization 场景；状态可序列化；现有 CLI 行为不变。

### 任务 27：定义 StatePatch、Reducer、调用身份和 Trace 协议

**目标：** 在引入运行时前冻结状态增量、重放、调用关联和运行证据语义。

**涉及模块：** state patch、transition policy、reducer、TraceEvent schema、运行标识。

**前置依赖：** 任务 26。

**步骤流程：**

1. 定义带 `patch_id` 的 `StatePatch` 和各字段写入阶段。
2. 定义 overwrite、append、按业务 ID 合并、冲突和失效规则。
3. 用纯 Python reducer 实现 phase 校验和重复 patch 去重。
4. 定义 `node_id + logical_call_id + attempt`，logical call ID 不随重试变化。
5. 扩展项目 `TraceEvent` 的 runtime、node、attempt、logical_call_id 字段。
6. 测试重复 patch、非法跳转和 trace JSON round-trip。

**验证命令：** `uv run pytest tests/test_workflow_reducer.py tests/test_trace_runtime_fields.py -v`

**验收标准：** reducer 不依赖框架；重复 patch 不重复追加；非法转换结构化失败；LangGraph 接入前 trace schema 已稳定。

### 任务 28：建立 CapabilityGateway 端口和 ToolExecutor 适配

**目标：** 在图运行时前建立统一能力边界，避免 ToolNode 或 Agent 绕过现有治理。

**涉及模块：** capability contracts、gateway port、ToolExecutor adapter、幂等测试。

**前置依赖：** 任务 27。

**步骤流程：**

1. 定义 `CapabilityRequest/Result/Policy/Error` 和 async `CapabilityGateway.execute()`。
2. 声明 `read_only_repeatable`、`deterministic`、`side_effecting` 幂等等级。
3. 用 adapter 包装现有 `ToolExecutor`，保持 schema、caller、timeout、错误和 trace 行为。
4. 使用任务 27 的 logical call ID 处理重复调用，`attempt` 只记录物理重试。
5. 对政策检索、待遇计算、非法 caller、超时和重复执行运行 contract tests。

**验证命令：** `uv run pytest tests/test_capability_gateway_contract.py tests/test_tool_executor.py -v`

**验收标准：** Agent/Runtime 只依赖 gateway port；现有工具行为不变；相同逻辑调用不会产生不可解释的重复执行。

### 任务 29：阶段化 Native Runtime 并建立 Runtime Contract

**目标：** 将现有 orchestrator 拆成阶段服务，并让 CLI/Eval 依赖 `WorkflowRuntime` 端口。

**涉及模块：** application stages、Native Runtime、Runtime port、组合根、CLI、EvalRunner。

**前置依赖：** 任务 28。

**步骤流程：**

1. 每个阶段接收 `WorkflowState`，返回 `StatePatch`。
2. Native Runtime 使用项目 reducer 串行推进阶段。
3. 定义 async `WorkflowRuntime.invoke()`，组合根默认装配 Native Runtime。
4. CLI 和 EvalRunner 只依赖 Runtime port。
5. 建立单 runtime contract suite，覆盖完成、追问、能力失败、安全拦截、StopReason、CapabilityRequest 和 TraceEvent。

**验证命令：** `uv run pytest tests/runtime_contracts tests/test_cli_ask.py tests/test_cli_eval.py -v`

**验收标准：** `ask()` 不再原地修改大状态对象；阶段可独立测试；CLI/Eval 不依赖具体 runtime；无 LangGraph 依赖。

### 任务 30：接入最小串行 LangGraph Runtime

**目标：** 只映射已经稳定的项目阶段和协议，并将 LangGraph 设为默认可配置运行时。

**涉及模块：** `pyproject.toml`、`uv.lock`、`runtimes/langgraph`、runtime 配置和 contract tests。

**前置依赖：** 任务 29。

**步骤流程：**

1. 使用 `uv add` 安装最小 LangGraph 依赖并锁定版本。
2. 实现 `WorkflowState` 与 graph state 的 adapter 投影。
3. 注册薄节点：节点只调用阶段服务并返回项目 patch。
4. Graph 执行继续调用项目 reducer 和 CapabilityGateway。
5. 配置默认 `runtime=langgraph`，保留显式 `runtime=native`。
6. 运行同一 runtime contract suite；不启用 ToolNode 直连、checkpoint、interrupt 或并行。

**验证命令：**

```bash
uv run pytest tests/runtime_contracts -v
uv run pytest tests/test_runtime_selection.py -v
```

**验收标准：** 默认选择 LangGraph；Native 可切换；两个实现通过单 runtime contract；项目公共模块没有 LangGraph 导入。

### 任务 31：双运行时差分验收

**目标：** 比较两个运行时的业务语义，不重复维护单 runtime contract。

**涉及模块：** differential runner、trace mapper、comparison artifact、EvalRunner。

**前置依赖：** 任务 30。

**步骤流程：**

1. 同一 `RunRequest` 分别运行 Native 和 LangGraph。
2. 规范化比较 WorkflowResult、StopReason、状态字段、CapabilityRequest 和项目关键事件。
3. 允许差异仅限 runtime 名称、节点内部时序、checkpoint ID 和毫秒级时间。
4. 输出结构化差异 artifact；业务字段、证据、调用参数和安全结果不允许差异。
5. 对 30+ eval cases 执行双运行时差分。

**验证命令：** `uv run pytest tests/test_runtime_differential.py -v && uv run ananhu-agent eval data/eval/eval_cases.jsonl --runtime both`

**验收标准：** 无禁止差异；项目 trace 是两种运行时共同事实源；EvalRunner 不读取 LangGraph 内部对象。

### 任务 32：接入真实 ModelGateway

**目标：** 以项目模型端口接入一个真实 provider，不依赖 LangGraph 模型封装。

**涉及模块：** ModelGateway、provider adapter、配置、usage、opt-in smoke。

**前置依赖：** 任务 31。

**步骤流程：** 定义 provider-neutral 请求响应；适配真实模型；记录 token/费用/错误；保留 Fake Model；建立无 key skip 和有 key smoke。

**验证命令：** `uv run pytest tests/test_model_gateway_contract.py -v`；真实 smoke 使用显式环境变量运行。

**验收标准：** Native/LangGraph 复用同一 gateway；无 key CI 不失败；真实结果和 fake 指标分开报告。

### 任务 33：建立真实 KnowledgeGateway 与政策基线

**目标：** 建立带可信元数据和引用的政策检索基线，暂不因技术展示引入向量库。

**涉及模块：** policy corpus、KnowledgeGateway、lexical baseline、EvidenceItem、RAG eval。

**前置依赖：** 任务 31。

**步骤流程：** 建立 jurisdiction/有效期/审核/版本元数据；实现检索前过滤；实现 lexical baseline；输出 EvidenceItem；评测召回和引用支持；由数据决定后续是否增加向量与 reranker。

**验证命令：** `uv run pytest tests/test_knowledge_gateway_contract.py tests/test_policy_corpus_quality.py tests/test_rag_eval.py -v`

**验收标准：** 模型提及地区不能改变可信范围；证据可追溯；无结果不编造；两个 runtime 复用同一 gateway。

### 任务 34：运行真实咨询 Smoke Eval

**目标：** 组合真实 ModelGateway 和 KnowledgeGateway，验证最小咨询链路并暴露真实失败。

**涉及模块：** smoke dataset、EvalRunner、Usage、Badcase、文档验收。

**前置依赖：** 任务 32、任务 33。

**步骤流程：** 建立 6-10 条专家确认场景；分别运行 Native/LangGraph；记录模型、检索、引用、安全、token 和延迟；失败写入分类 badcase；更新真实验收说明。

**验证命令：** `ANANHU_REAL_MODEL_SMOKE=1 uv run ananhu-agent eval data/eval/real_smoke_cases.jsonl --runtime both`

**验收标准：** 两个 runtime 使用相同真实能力；指标按机制分层；失败可定位；不把 smoke 结果描述为生产质量。

## 3. 条件任务：Checkpoint 与恢复

只有出现跨请求暂停恢复、人工审批后续跑或长流程故障恢复中的至少一个真实需求，才创建独立 checkpoint 任务。届时必须先定义 `CheckpointEnvelope`、版本兼容、状态迁移、损坏处理和 side-effecting capability 幂等，再启用 LangGraph checkpointer。

## 4. 对抗性审查清单

1. 是否出现 LangGraph/供应商类型泄漏到公共协议。
2. 是否形成 Native 与 Graph 双状态机或双 reducer。
3. 是否把 Agent 机械映射为节点。
4. 是否绕过 CapabilityGateway。
5. 是否混淆 Case、Session、Run、Checkpoint 和 Trace。
6. 是否存在任务使用后置任务才定义的类型或语义。
7. 是否在没有 eval 证据时增加向量、reranker、planner 或并行。
8. 是否把 fake/smoke 指标描述为生产效果。

## 5. 总体验收

- LangGraph 默认、Native 可切换，两者通过同一 contract 和差分 eval。
- domain/application/Agent/Capability/Eval 公共模块不导入 LangGraph、Agno 或 provider SDK。
- 状态、reducer、调用身份、能力治理、trace 和 eval 由项目协议定义。
- 移除 LangGraph 后，案件事实、工具、知识、Prompt、Trace、Usage、Badcase 和 Eval 仍可复用。
