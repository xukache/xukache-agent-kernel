# KnowledgeCapability 直接改造实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `pm-workflow:subagent-driven-development`（推荐）或 `pm-workflow:executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

> **执行状态（2026-07-11）：** 任务 1-9 的代码迁移、文档迁移、反向验证和三轮修订已完成；当前唯一未执行项是用户授权后的最终提交/合并。Native/LangGraph 复用同一 CapabilityGateway 实现和注册协议，但各自保持独立实例与幂等缓存。

**目标：** 在 v0.9 中删除 `PolicyRAGTool`、`search_policy()`、旧 `documents` 输出和 `ToolExecutor` 兼容适配，把政策检索直接改造成 `knowledge.search` 能力，同时让 Native/LangGraph 继续通过同一 CapabilityGateway 实现和注册协议执行，并保持治理、证据、trace、幂等和差分验收语义一致。

**架构：** Agent 只生成轻量的 `CapabilityCall` 意图；阶段服务补齐运行身份、节点、逻辑调用 ID 和 attempt 后构造 `CapabilityRequest`。`CapabilityGateway` 直接执行显式注册的 `knowledge.search` 与 `payment.calculate`，知识能力调用注入的 `KnowledgeGateway`，不再经过旧工具名、旧 handler 或旧结果投影。`CapabilityResult.output` 是唯一结构化能力结果来源，政策结果直接使用 `EvidenceItem` 集合，答案聚合和 `WorkflowState.evidence` 不再读取 `documents`。

**技术栈：** Python 3.11、`uv`、Pydantic、async `CapabilityGateway`、`KnowledgeGateway` / `LexicalKnowledgeGateway`、Native Runtime、LangGraph Runtime、pytest、离线 RAG eval 和 Native/LangGraph differential eval。

---

## 1. 基线与不可协商决策

### 1.1 基线

- 基线架构版本：v0.8。
- 基线版本正文：`docs/architecture/versions/v0.8-knowledge-gateway-policy-baseline.md`。
- 当前任务分支：`mvp-direct-knowledge-capability-plan`。
- 实现分支命名建议：`mvp-direct-knowledge-capability-v09`。
- 当前全量基线：`uv run pytest -q`，预期 `204 passed, 1 skipped`。
- 当前离线双运行时基线：`total: 30`、`equivalent: 30`、`different: 0`。

v0.8 的历史正文必须保持只读。它明确记录了 `PolicyRAGTool` 兼容适配，这个事实不能通过改写历史文档消除。v0.9 的新架构正文必须完整描述删除兼容层后的状态。

### 1.2 直接改造决策

本次是破坏性内部协议升级，不提供过渡期兼容逻辑：

1. 删除 `PolicyRAGTool`、`search_policy()`、`KnowledgeQuery.from_payload()` 和 `KnowledgeSearchResult.to_tool_payload()`。
2. 删除 `ToolCallRequest`、`ToolCallResult` 及 `CapabilityResult.tool_call_result` 这种旧工具协议投影；统一使用 `CapabilityCall`、`CapabilityRequest`、`CapabilityResult`。
3. 删除 `ToolExecutorCapabilityGateway`、`ToolRegistry`、`ToolDefinition` 和旧 `ToolExecutor` 适配路径；能力治理直接由新的能力注册和执行实现承担。
4. 能力名称使用 `knowledge.search` 和 `payment.calculate`，不得同时接受旧名称。
5. 政策结果只允许从 `CapabilityResult.output["evidences"]` 读取；禁止新增 `documents` 别名、双写字段、读取 fallback 或输入格式兼容分支。
6. Agent 不直接调用 `KnowledgeGateway`，必须先返回 `CapabilityCall`，再由阶段服务调用 `CapabilityGateway`。
7. KnowledgeGateway 继续负责可信 jurisdiction、审核状态、有效期、来源类型和版本过滤；CapabilityGateway 负责能力白名单、caller 权限、输入输出校验、超时、幂等和 capability trace。
8. 待遇测算同时迁移到 `payment.calculate`，避免保留一条“政策能力是新协议、测算能力仍是旧工具协议”的双轨路径。
9. Native 与 LangGraph 复用同一阶段服务、同一 `CapabilityGateway` 实现和同一组合根注册协议；每个 runtime 保持独立网关实例与幂等缓存，避免差分运行互相污染。允许 trace 的 runtime 名称、事件 ID、时间和延迟不同，不允许能力名、输入、Evidence ID、StopReason 或最终业务状态不同。

### 1.3 明确不做

- 不引入向量数据库、embedding、fusion、reranker 或在线抓取。
- 不引入通用动态插件发现、复杂能力编排 DSL 或第二套 reducer。
- 不保留旧工具名的只读别名。
- 不在 v0.9 期间修改 v0.8 历史架构正文。
- 不把真实 provider Smoke Eval 混入离线能力协议迁移的通过条件；真实 provider 仅作为单独边界验证。

---

## 2. 文件清单与职责

### 2.1 能力与知识协议

- 修改：`ananhu_agent/capabilities/contracts.py`
  - 保留 `CapabilityRequest`、`CapabilityResult`、策略、错误和网关端口。
  - 删除 `tool_call_result`。
  - 明确能力版本、输出、错误和幂等字段。
- 创建：`ananhu_agent/capabilities/registry.py`
  - 定义 `CapabilityDefinition` 和显式 `CapabilityRegistry`。
  - 保存名称、描述、风险等级、超时、允许 caller、输入键、输出键和 handler。
- 创建：`ananhu_agent/capabilities/default_gateway.py`
  - 直接实现 `CapabilityGateway`。
  - 执行注册能力的权限、输入输出校验、超时、幂等和 capability started/finished/failed 事件。
- 删除：`ananhu_agent/capabilities/tool_executor_gateway.py`
  - 不保留适配器别名或包装类。
- 修改：`ananhu_agent/capabilities/__init__.py`
  - 只导出新的能力协议、注册表和默认网关。

### 2.2 Agent 与运行时协议

- 修改：`ananhu_agent/schemas.py`
  - 用 `CapabilityCall` 替换 `ToolCallRequest`。
  - 用 `AgentMessage.capability_calls` 替换 `tool_calls`。
  - 用 `AgentContext.capability_results` 替换 `tool_results`。
- 修改：`ananhu_agent/ports/knowledge_gateway.py`
  - 删除 `KnowledgeQuery.from_payload()`。
  - 删除 `KnowledgeSearchResult.to_tool_payload()`。
  - 保留 `KnowledgeQuery`、`EvidenceItem`、`KnowledgeSearchResult` 的结构化端口语义。
- 修改：`ananhu_agent/agents/policy_rag.py`
  - 生成 `capability_name="knowledge.search"` 的 `CapabilityCall`。
- 修改：`ananhu_agent/agents/payment_calculation.py`
  - 生成 `capability_name="payment.calculate"` 的 `CapabilityCall`。
- 修改：`ananhu_agent/agents/domain_consultation.py`
  - 只保留领域输出和是否需要政策证据的声明，不直接触碰知识端口。
- 修改：`ananhu_agent/runtimes/native/stages.py`
  - 将 `CapabilityCall` 转换为 `CapabilityRequest`。
  - 从 `CapabilityResult.output["evidences"]` 构造状态证据。
  - 删除所有旧工具名和 `ToolCallResult` 转换。
- 修改：`ananhu_agent/runtimes/native/runtime.py`
  - 仅使用新的 capability 结果和运行证据。
- 修改：`ananhu_agent/runtimes/langgraph/runtime.py`
  - 继续只调度项目阶段，不新增 LangGraph 专属能力协议。

### 2.3 组合根与业务输出

- 修改：`ananhu_agent/runtime.py`
  - 直接注册 `knowledge.search` 和 `payment.calculate`。
  - 注入 `KnowledgeGateway` 到 `knowledge.search` handler。
  - 移除 `search_policy`、`ToolRegistry` 和 `ToolExecutor` 依赖。
- 修改：`ananhu_agent/orchestrator/aggregator.py`
  - 从 `CapabilityResult.output["evidences"]` 聚合政策证据。
  - 继续从 `payment.calculate` 聚合测算结果。
- 修改：`ananhu_agent/orchestrator/badcase_rules.py`
  - 按 `capability_name == "knowledge.search"` 判断无结果。
- 修改：`ananhu_agent/workflow/contracts.py`
  - 更新 capability result 和 evidence 字段说明，删除旧工具名。
- 修改：`ananhu_agent/cli/main.py`
  - 输出 capability 名称，不再输出 `tool_calls`。
- 修改：`ananhu_agent/cli/tui/app.py`
  - 展示 capability 调用信息，不再从旧工具字段读取。
- 删除：`ananhu_agent/tools/policy_rag.py`
  - 旧函数和同步兼容入口不再存在。
- 删除或迁移：`ananhu_agent/tools/executor.py`、`ananhu_agent/tools/registry.py`
  - 旧工具执行层的治理代码迁移到新的 capability registry/gateway 后删除；不能留下未使用的兼容实现。

### 2.4 测试与架构文档

- 创建：`tests/test_capability_registry.py`
- 创建：`tests/test_default_capability_gateway.py`
- 修改：`tests/test_knowledge_gateway_contract.py`
- 修改：`tests/test_business_agents.py`
- 修改：`tests/test_schemas.py`
- 修改：`tests/test_workflow_reducer.py`
- 修改：`tests/test_workflow_contracts.py`
- 修改：`tests/test_answer_governance.py`
- 修改：`tests/test_answer_governance_extended.py`
- 修改：`tests/test_trace_runtime_fields.py`
- 修改：`tests/test_cli_feedback_badcase.py`
- 修改：`tests/runtime_contracts/test_native_runtime_contract.py`
- 删除：`tests/test_tool_executor.py`
- 删除：`tests/test_capability_gateway_contract.py`
- 删除：`tests/test_mvp_tools.py`
- 创建：`tests/test_direct_capability_migration.py`
- 创建：`docs/architecture/versions/v0.9-direct-knowledge-capability.md`
- 修改：`docs/architecture/02-agent-runtime.md`
- 修改：`docs/architecture/04-tools-models.md`
- 修改：`docs/architecture/05-data-observability.md`
- 修改：`docs/architecture/99-changelog.md`
- 修改：`TECH_ARCHITECTURE_MVP.md`
- 修改：`docs/architecture.md`

---

## 3. 原子任务清单

### 任务 1：冻结 v0.9 能力协议和旧符号删除测试

**状态：已完成（代码和测试已落地，未提交）。**

**文件：**
- 创建：`tests/test_direct_capability_migration.py`
- 修改：`ananhu_agent/capabilities/contracts.py`
- 修改：`ananhu_agent/schemas.py`
- 修改：`ananhu_agent/ports/knowledge_gateway.py`

- [x] **步骤 1：先写失败测试，冻结新协议和旧符号不存在。**

```python
def test_agent_message_exposes_capability_calls_only():
    from ananhu_agent.schemas import AgentMessage

    message = AgentMessage(agent_name="x", status="success", content="x")
    assert message.capability_calls == []
    assert not hasattr(message, "tool_calls")


def test_capability_result_has_no_legacy_tool_projection():
    from ananhu_agent.capabilities.contracts import CapabilityResult

    fields = CapabilityResult.model_fields
    assert "tool_call_result" not in fields


def test_legacy_knowledge_symbols_are_removed():
    from pathlib import Path

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("ananhu_agent").rglob("*.py")
    )
    for symbol in (
        "PolicyRAG" + "Tool",
        "search_" + "policy",
        "ToolCall" + "Request",
        "ToolCall" + "Result",
    ):
        assert symbol not in source
```

该测试只扫描产品 Python 代码，避免测试自身为了断言旧符号而制造假阳性；任务 7 的 shell 扫描再覆盖 `ananhu_agent` 和 `tests` 两个目录。

- [x] **步骤 2：运行测试确认失败。**

运行：

```bash
uv run pytest tests/test_direct_capability_migration.py -q
```

预期：FAIL；现有 `AgentMessage.tool_calls`、`CapabilityResult.tool_call_result` 和旧符号仍存在。

- [x] **步骤 3：编写最少协议实现。**

`ananhu_agent/schemas.py` 的目标形状：

```python
class CapabilityCall(BaseModel):
    """Agent 声明一次能力意图；运行身份由阶段服务补齐。"""

    call_id: str
    capability_name: str
    called_by: str
    input: dict[str, Any]


class AgentMessage(BaseModel):
    agent_name: str
    status: Literal["success", "failed", "need_clarification"]
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    capability_calls: list[CapabilityCall] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

`CapabilityResult` 删除 `tool_call_result`，`KnowledgeQuery` 和 `KnowledgeSearchResult` 删除旧 payload 转换方法。调用方必须显式构造 Pydantic 请求，不接受任意旧字典。

- [x] **步骤 4：运行测试确认通过。**

运行：

```bash
uv run pytest tests/test_direct_capability_migration.py -q
```

预期：PASS；此时业务旧调用方会因引用旧字段而失败，这是下一任务的明确输入。

- [x] **步骤 5：用户授权后统一收尾提交协议变更。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 2：建立显式 CapabilityRegistry，迁移治理语义

**状态：已完成（代码和测试已落地，未提交）。**

**文件：**
- 创建：`ananhu_agent/capabilities/registry.py`
- 创建：`tests/test_capability_registry.py`
- 修改：`ananhu_agent/capabilities/contracts.py`
- 修改：`ananhu_agent/capabilities/__init__.py`

- [x] **步骤 1：先写失败测试。**

```python
def test_registry_accepts_only_explicit_capability_names():
    from ananhu_agent.capabilities.registry import CapabilityDefinition, CapabilityRegistry

    registry = CapabilityRegistry()
    registry.register(
        CapabilityDefinition(
            name="knowledge.search",
            description="检索政策证据",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=["PolicyRAGAgent"],
            required_input_keys=["query", "trusted_jurisdiction"],
            output_required_keys=["evidences", "no_result_reason"],
            handler=lambda payload: payload,
        )
    )

    assert registry.get("knowledge.search").name == "knowledge.search"
    assert registry.get("PolicyRAGTool") is None
```

- [x] **步骤 2：运行测试确认失败。**

运行：

```bash
uv run pytest tests/test_capability_registry.py -q
```

预期：FAIL；`CapabilityRegistry` 和 `CapabilityDefinition` 尚不存在。

- [x] **步骤 3：实现显式注册模型。**

```python
@dataclass(frozen=True)
class CapabilityDefinition:
    name: str
    description: str
    risk_level: str
    timeout_ms: int
    allowed_callers: tuple[str, ...]
    required_input_keys: tuple[str, ...]
    output_required_keys: tuple[str, ...]
    handler: CapabilityHandler


class CapabilityRegistry:
    def register(self, definition: CapabilityDefinition) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"duplicate capability: {definition.name}")
        self._definitions[definition.name] = definition

    def get(self, name: str) -> CapabilityDefinition | None:
        return self._definitions.get(name)
```

能力名只注册 `knowledge.search`、`payment.calculate`；不写旧名映射。字段使用能力语义，不再出现 `tool_name`、`tool_status`、`tool_error_code`。

- [x] **步骤 4：运行测试确认通过。**

运行：

```bash
uv run pytest tests/test_capability_registry.py -q
```

预期：PASS。

- [x] **步骤 5：用户授权后统一收尾提交注册表。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 3：直接实现 DefaultCapabilityGateway

**状态：已完成（代码和测试已落地，未提交）。**

**文件：**
- 创建：`ananhu_agent/capabilities/default_gateway.py`
- 创建：`tests/test_default_capability_gateway.py`
- 删除：`ananhu_agent/capabilities/tool_executor_gateway.py`
- 删除：`ananhu_agent/tools/executor.py`
- 删除：`ananhu_agent/tools/registry.py`
- 修改：`ananhu_agent/capabilities/__init__.py`

- [x] **步骤 1：先写失败测试，覆盖成功、非法能力、非法 caller、缺输入、输出校验、超时、幂等和 trace。**

```python
def test_knowledge_capability_returns_structured_evidence(tmp_path):
    gateway = build_gateway(tmp_path)
    result = asyncio.run(gateway.execute(_request("knowledge.search")))

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["evidences"]
    assert "documents" not in result.output
    assert result.logical_call_id == "call_1"


def test_legacy_capability_name_is_not_registered(tmp_path):
    gateway = build_gateway(tmp_path)
    result = asyncio.run(gateway.execute(_request("PolicyRAGTool")))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_not_registered"


def test_illegal_caller_is_rejected_before_handler(tmp_path):
    gateway = build_gateway(tmp_path)
    result = asyncio.run(
        gateway.execute(_request("knowledge.search", caller="PaymentCalculationAgent"))
    )

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "caller_not_allowed"


def test_same_logical_call_reuses_result_and_only_one_handler_run(tmp_path):
    gateway = build_gateway(tmp_path)
    first = asyncio.run(gateway.execute(_request("knowledge.search", attempt=1)))
    retry = asyncio.run(gateway.execute(_request("knowledge.search", attempt=2)))

    assert first.status is CapabilityStatus.SUCCESS
    assert retry.reused is True
    assert retry.attempt == 2
    # 每个物理 attempt 都有独立生命周期事件；第二次只复用结果，不重复执行 handler。
    assert len([row for row in gateway.trace_recorder.read_all() if row["event_type"] == "capability_finished"]) == 2
```

测试文件必须在同一文件内定义 `build_gateway(tmp_path)`、`_request(capability_name, caller="PolicyRAGAgent", attempt=1)` 和一个带计数器的异步 knowledge handler；不得依赖生产代码中的隐式 fixture。

- [x] **步骤 2：运行测试确认失败。**

运行：

```bash
uv run pytest tests/test_default_capability_gateway.py -q
```

预期：FAIL；新的网关不存在，且当前 trace 仍写 `tool_called/tool_finished`。

- [x] **步骤 3：实现最小直接网关。**

核心执行顺序固定为：

```text
capability lookup
  -> caller permission
  -> required input
  -> logical_call_id cache
  -> timeout
  -> handler
  -> required output
  -> capability trace
```

`DefaultCapabilityGateway.execute()` 只接受 `CapabilityRequest`，直接调用 `CapabilityDefinition.handler`。handler 可以是 async；同步的待遇测算 handler 通过现有线程池边界执行。`knowledge.search` handler 返回：

```python
{
    "evidences": [evidence.model_dump(mode="json") for evidence in result.evidences],
    "corpus_version": result.corpus_version,
    "applied_filters": result.applied_filters,
    "no_result_reason": result.no_result_reason,
}
```

失败结果使用 `CapabilityResult.error`，事件类型只使用 `capability_started`、`capability_finished`、`capability_failed`。幂等缓存键至少包含 `(run_id, logical_call_id)`，`attempt` 只记录物理尝试。

- [x] **步骤 4：运行专项网关测试。**

运行：

```bash
uv run pytest tests/test_default_capability_gateway.py -v
```

预期：全部 PASS；非法能力、非法 caller、缺输入、超时和重复逻辑调用都返回结构化错误，不抛出底层异常。

- [x] **步骤 5：用户授权后统一收尾提交网关。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一删除确认；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 4：把 KnowledgeGateway 接入 `knowledge.search`

**状态：已完成（代码和测试已落地，未提交）。**

**文件：**
- 修改：`ananhu_agent/ports/knowledge_gateway.py`
- 修改：`ananhu_agent/infrastructure/knowledge/lexical_gateway.py`
- 修改：`ananhu_agent/runtime.py`
- 修改：`tests/test_knowledge_gateway_contract.py`
- 修改：`tests/test_rag_eval.py`
- 修改：`tests/test_policy_corpus_quality.py`

- [x] **步骤 1：先写失败测试，锁定调用输入和直接 Evidence 输出。**

```python
def test_knowledge_search_receives_trusted_jurisdiction_not_model_region():
    gateway = RecordingKnowledgeGateway()
    result = asyncio.run(
        gateway.search(
            KnowledgeQuery(
                query="工伤待遇",
                jurisdiction={"province": "四川省", "city": None},
            )
        )
    )

    assert gateway.requests[0].jurisdiction == {"province": "四川省", "city": None}
    assert result.evidences
    assert result.no_result_reason is None
```

`RecordingKnowledgeGateway` 是测试文件内的最小 `KnowledgeGateway` double：保存每次 `KnowledgeQuery` 到 `requests`，返回一条固定的 `EvidenceItem`。它不读取模型地区字段，用于直接断言 handler 构造出的可信 jurisdiction。

- [x] **步骤 2：运行测试确认失败。**

运行：

```bash
uv run pytest tests/test_knowledge_gateway_contract.py tests/test_rag_eval.py -q
```

预期：FAIL；旧测试仍通过 `search_policy()` 或 `documents` 读取，新的能力 handler 尚未连接。

- [x] **步骤 3：实现直接 handler 和组合根注册。**

组合根中的能力定义使用明确闭包：

```python
async def search_knowledge(payload: dict[str, Any]) -> dict[str, Any]:
    query = KnowledgeQuery(
        query=payload["query"],
        tenant=payload.get("tenant", "default"),
        jurisdiction=payload["trusted_jurisdiction"],
        effective_at=payload.get("effective_at"),
        review_status="approved",
        audience_role=payload.get("audience_role", "public"),
        source_type=payload.get("source_type", "official"),
        document_version=payload.get("document_version"),
        top_k=payload.get("top_k", 3),
    )
    result = await knowledge_gateway.search(query)
    return {
        "evidences": [item.model_dump(mode="json") for item in result.evidences],
        "corpus_version": result.corpus_version,
        "applied_filters": result.applied_filters,
        "no_result_reason": result.no_result_reason,
    }
```

不得从 payload 读取模型自行抽取的 `province` / `city` 覆盖 `trusted_jurisdiction`。无可信地区时原样传入空 jurisdiction，让 KnowledgeGateway 返回 `no_trusted_jurisdiction_match`。

- [x] **步骤 4：运行知识与 RAG 测试。**

运行：

```bash
uv run pytest tests/test_knowledge_gateway_contract.py tests/test_policy_corpus_quality.py tests/test_rag_eval.py -v
```

预期：知识契约、语料质量和 RAG eval 全部 PASS；Recall@K、MRR、引用支持率和可信过滤率保持 v0.8 基线。

- [x] **步骤 5：用户授权后统一收尾提交 KnowledgeCapability 接入。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 5：迁移 Agent、阶段服务和双运行时

**状态：已完成（代码和测试已落地，未提交）。**

**文件：**
- 修改：`ananhu_agent/agents/policy_rag.py`
- 修改：`ananhu_agent/agents/payment_calculation.py`
- 修改：`ananhu_agent/runtimes/native/stages.py`
- 修改：`ananhu_agent/runtimes/native/runtime.py`
- 修改：`ananhu_agent/runtimes/langgraph/runtime.py`
- 修改：`ananhu_agent/workflow/contracts.py`
- 修改：`tests/test_business_agents.py`
- 修改：`tests/test_workflow_reducer.py`
- 修改：`tests/test_workflow_contracts.py`
- 修改：`tests/runtime_contracts/test_native_runtime_contract.py`

- [x] **步骤 1：先写失败测试，覆盖新能力名、Evidence 合并和双运行时语义。**

```python
def test_policy_agent_requests_knowledge_search():
    message = PolicyRAGAgent().run(
        AgentContext.new_for_query("sess_1", 1, "劳动能力鉴定需要哪些材料？")
    )

    assert [call.capability_name for call in message.capability_calls] == ["knowledge.search"]
    assert message.capability_calls[0].called_by == "PolicyRAGAgent"


def test_payment_agent_requests_payment_calculate():
    message = PaymentCalculationAgent().run(
        AgentContext.new_for_query("sess_1", 1, "四川十级工伤月工资6000赔多少钱？")
    )

    assert [call.capability_name for call in message.capability_calls] == ["payment.calculate"]


def test_workflow_evidence_is_merged_by_evidence_id_not_documents():
    patch = StatePatch(
        patch_id="patch_1",
        run_id="run_1",
        source_phase=WorkflowPhase.EXECUTE,
        next_phase=WorkflowPhase.VALIDATE_EVIDENCE,
        node_id="execute",
        logical_call_id="call_1",
        capability_results=[{"capability_name": "knowledge.search", "status": "success"}],
        evidence=[{"evidence_id": "ev_1", "content": "可信原文"}],
    )
    result = reduce_workflow_state(
        WorkflowState(
            run_id="run_1",
            request_id="req_1",
            session_id="sess_1",
            phase=WorkflowPhase.EXECUTE,
        ),
        patch,
    )

    assert result.ok
    assert result.state.evidence == [{"evidence_id": "ev_1", "content": "可信原文"}]
```

测试文件必须显式导入 `WorkflowState`、`WorkflowPhase`、`StatePatch` 和 `reduce_workflow_state`；不得依赖未在测试文件定义的 `initial_state()`。

- [x] **步骤 2：运行测试确认失败。**

运行：

```bash
uv run pytest tests/test_business_agents.py tests/test_workflow_reducer.py tests/runtime_contracts/test_native_runtime_contract.py -q
```

预期：FAIL；Agent 仍返回 `tool_calls`，阶段服务仍按 `PolicyRAGTool` 分支，状态结果仍是旧 `ToolCallResult` 形状。

- [x] **步骤 3：迁移执行链路。**

`NativeStageServices._execute_capabilities()` 的转换目标：

```python
for call in message.capability_calls:
    result = await self.capability_gateway.execute(
        CapabilityRequest(
            run_id=state.run_id,
            request_id=self.ctx.request.request_id,
            session_id=self.ctx.request.session_id,
            capability_name=call.capability_name,
            caller=call.called_by,
            input=call.input,
            node_id=node_id,
            logical_call_id=call.call_id,
            attempt=1,
            runtime_name=self.runtime_name,
            runtime_version=self.runtime_version,
        )
    )
    self.ctx.capability_results.append(result)
```

计划、校验证据和 compose 阶段只判断：

```python
result.capability_name == "knowledge.search"
result.status is CapabilityStatus.SUCCESS
result.output.get("evidences", [])
```

`WorkflowState.capability_results` 保存 `CapabilityResult.model_dump(mode="json")`，`WorkflowState.evidence` 按 `evidence_id` 合并 `evidences`。Native 与 LangGraph 使用相同 `NativeStageServices`，不得在 LangGraph 图内新增 capability 路由。

- [x] **步骤 4：运行运行时契约和差分测试。**

运行：

```bash
uv run pytest tests/test_business_agents.py tests/test_workflow_reducer.py tests/test_workflow_contracts.py tests/runtime_contracts/test_native_runtime_contract.py -v
```

预期：全部 PASS；两个运行时的 capability 名称、输入、Evidence ID、最终 StopReason 和业务状态等价。

- [x] **步骤 5：用户授权后统一收尾提交运行时迁移。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 6：迁移答案治理、badcase、CLI 和 TUI

**状态：已完成（代码和测试已落地，未提交）。**

**文件：**
- 修改：`ananhu_agent/orchestrator/aggregator.py`
- 修改：`ananhu_agent/orchestrator/badcase_rules.py`
- 修改：`ananhu_agent/cli/main.py`
- 修改：`ananhu_agent/cli/tui/app.py`
- 修改：`tests/test_answer_governance.py`
- 修改：`tests/test_answer_governance_extended.py`
- 修改：`tests/test_trace_runtime_fields.py`
- 修改：`tests/test_cli_feedback_badcase.py`

- [x] **步骤 1：先写失败测试，锁定最终答案只读 EvidenceItem。**

```python
def test_final_answer_reads_evidences_from_knowledge_capability():
    ctx = AgentContext.new_for_query("sess_1", 1, "上班路上交通事故算工伤吗？")
    ctx.capability_results.append(
        CapabilityResult(
            request_id="req_1",
            session_id="sess_1",
            capability_name="knowledge.search",
            caller="PolicyRAGAgent",
            node_id="execute",
            logical_call_id="call_1",
            attempt=1,
            status=CapabilityStatus.SUCCESS,
            policy=CapabilityPolicy(
                risk_level="read_only",
                timeout_ms=3000,
                idempotency=CapabilityIdempotency.READ_ONLY_REPEATABLE,
            ),
            output={
                "evidences": [{
                    "content": "上下班途中非本人主要责任交通事故应认定为工伤。",
                    "citation": {
                        "title": "工伤保险条例",
                        "article": "第十四条",
                        "source_url": "https://example.com/policy",
                        "document_version": "v1",
                        "evidence_id": "ev_1",
                        "province": "四川省",
                        "city": "",
                    },
                }]
            },
        )
    )

    answer = build_final_answer(ctx)

    assert "工伤保险条例" in answer
    assert "以经办机构和正式材料为准" in answer


def test_legacy_documents_projection_is_ignored_or_rejected():
    ctx = AgentContext.new_for_query("sess_1", 1, "工伤政策")
    ctx.capability_results.append(
            CapabilityResult(
                request_id="req_1",
                session_id="sess_1",
                capability_name="knowledge.search",
                caller="PolicyRAGAgent",
                node_id="execute",
                logical_call_id="call_2",
                attempt=1,
                status=CapabilityStatus.SUCCESS,
                policy=CapabilityPolicy(
                    risk_level="read_only",
                    timeout_ms=3000,
                    idempotency=CapabilityIdempotency.READ_ONLY_REPEATABLE,
                ),
                output={"documents": [{"content": "不应被消费"}], "evidences": []},
            )
        )
    )

    answer = build_final_answer(ctx)

    assert "不应被消费" not in answer
    assert "不能给出确定结论" in answer
```

- [x] **步骤 2：运行测试确认失败。**

运行：

```bash
uv run pytest tests/test_answer_governance.py tests/test_answer_governance_extended.py -q
```

预期：FAIL；聚合器当前读取 `ToolCallResult.output["documents"]`。

- [x] **步骤 3：迁移消费端。**

```python
def _collect_policy_evidences(ctx: AgentContext) -> list[dict[str, Any]]:
    evidences: list[dict[str, Any]] = []
    for result in ctx.capability_results:
        if (
            result.capability_name == "knowledge.search"
            and result.status is CapabilityStatus.SUCCESS
        ):
            evidences.extend(result.output.get("evidences", []))
    return evidences
```

引用校验、地区不一致检查、无结果 badcase、CLI trace 展示和 TUI capability 列表全部改为新字段。任何缺失或空 `evidences` 都走保守答案，不读取 `documents`。

- [x] **步骤 4：运行治理和 CLI 测试。**

运行：

```bash
uv run pytest tests/test_answer_governance.py tests/test_answer_governance_extended.py tests/test_trace_runtime_fields.py tests/test_cli_feedback_badcase.py -v
```

预期：引用、地区 mismatch、无结果、精确金额承诺、安全拦截和 badcase 规则全部 PASS。

- [x] **步骤 5：用户授权后统一收尾提交业务消费端迁移。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 7：删除旧实现、旧测试和旧静态引用

**状态：已完成（代码和测试已落地，未提交）。**

**文件：**
- 删除：`ananhu_agent/tools/policy_rag.py`
- 删除：`tests/test_tool_executor.py`
- 删除：`tests/test_capability_gateway_contract.py`
- 删除：`tests/test_mvp_tools.py`
- 修改：所有 `ananhu_agent/**/*.py` 和 `tests/**/*.py` 中的旧字段引用
- 修改：`README.md`、CLI 帮助或项目代码注释中的当前实现说明

- [x] **步骤 1：先运行旧符号扫描，记录必须清零的代码范围。**

运行：

```bash
rg -n "PolicyRAGTool|search_policy|ToolCallRequest|ToolCallResult|ToolExecutor|ToolRegistry|ToolDefinition|tool_call_result|tool_calls|tool_name|output(\.get)?\(['\"]documents['\"]\)|['\"]documents['\"]\s*:|\bfrom_payload\b|\bto_tool_payload\b" ananhu_agent tests
```

预期：FAIL；输出当前所有旧符号位置。`docs/architecture/versions/v0.8-knowledge-gateway-policy-baseline.md` 不纳入扫描，因为它是只读历史快照。

- [x] **步骤 2：删除旧实现和旧测试入口。**

删除旧模块后，所有业务路径只能通过：

```text
Agent -> CapabilityCall -> NativeStageServices -> CapabilityRequest
     -> DefaultCapabilityGateway -> knowledge.search/payment.calculate
```

不得新增 `try/except ImportError`、`getattr(..., "tool_calls", ...)`、旧名 fallback 或测试专用别名。

- [x] **步骤 3：运行代码静态扫描确认清零。**

运行：

```bash
if rg -n "PolicyRAGTool|search_policy|ToolCallRequest|ToolCallResult|ToolExecutor|ToolRegistry|ToolDefinition|tool_call_result|tool_calls|tool_name|output(\.get)?\(['\"]documents['\"]\)|['\"]documents['\"]\s*:|\bfrom_payload\b|\bto_tool_payload\b" ananhu_agent tests; then
  exit 1
fi
```

预期：命令返回 0 且无输出。允许语料加载函数使用 `documents` 作为局部变量；禁止能力结果、状态、答案聚合和测试夹具继续使用 `documents` 输出投影。该命令只扫源码和测试；当前文档使用单独门禁，架构 changelog、v0.8 及更早版本正文、旧计划均属于历史事实。

```bash
if rg -n "PolicyRAGTool|search_policy|ToolExecutorCapabilityGateway|model_called|tool_success_rate|tool_failed|工具输入|工具输出|工具错误" \
  README.md AGENTS.md docs/backend-conventions.md \
  docs/architecture/02-agent-runtime.md docs/architecture/04-tools-models.md \
  docs/architecture/05-data-observability.md \
  docs/architecture/versions/v0.9-direct-knowledge-capability.md \
  ananhu_agent/prompts/templates; then
  exit 1
fi
```

- [x] **步骤 4：运行类型导入和全量测试。**

运行：

```bash
uv run pytest -q
```

预期：无收集错误；测试数量因删除旧测试而变化，但所有保留测试通过，失败只能来自尚未迁移的明确断言。

- [x] **步骤 5：用户授权后统一收尾提交删除旧兼容层。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 8：补齐反向路径、差分验证和真实 provider 边界

**状态：已完成（反向路径和离线差分已验证，未提交）。**

**文件：**
- 修改：`tests/test_direct_capability_migration.py`
- 修改：`tests/test_default_capability_gateway.py`
- 修改：`tests/test_knowledge_gateway_contract.py`
- 修改：`tests/runtime_contracts/test_native_runtime_contract.py`
- 修改：`data/eval/rag_cases.jsonl` 或对应无结果 fixture（仅在现有数据不足时）
- 修改：`docs/superpowers/plans/2026-07-11-direct-knowledge-capability-v0.9.md`

- [x] **步骤 1：补齐负向测试。**

必须有可执行测试覆盖：

```text
无 trusted jurisdiction -> no_trusted_jurisdiction_match
模型伪造 province/city -> 不覆盖 trusted_jurisdiction
无 lexical 结果 -> evidences=[] 且 no_result_reason 非空
过期文档 -> 不进入 evidences
未审核文档 -> 不进入 evidences
旧 capability 名 -> capability_not_registered
非法 caller -> caller_not_allowed
缺少 query/trusted_jurisdiction -> invalid_input_schema
handler 超时 -> capability_timeout
重试同一 logical_call_id -> reused=true 且只执行一次
Native/LangGraph -> 关键业务字段等价
旧符号静态扫描 -> 零命中
```

- [x] **步骤 2：运行专项负向测试确认通过。**

运行：

```bash
uv run pytest tests/test_direct_capability_migration.py tests/test_default_capability_gateway.py tests/test_knowledge_gateway_contract.py tests/runtime_contracts/test_native_runtime_contract.py -v
```

预期：所有负向测试 PASS；任何把旧字段重新塞回结果的实现都失败。

- [x] **步骤 3：运行离线 RAG 和双运行时差分。**

运行：

```bash
uv run pytest tests/test_knowledge_gateway_contract.py tests/test_policy_corpus_quality.py tests/test_rag_eval.py -v

ROOT="$(git rev-parse --show-toplevel)"
cd /tmp
ANANHU_PROMPT_TEMPLATE_DIR="$ROOT/ananhu_agent/prompts/templates" \
ANANHU_RUNTIME_DIR=/tmp/ananhu-verify-runtime-v09 \
uv run --project "$ROOT" ananhu-agent eval \
  "$ROOT/data/eval/eval_cases.jsonl" \
  --runtime both
```

预期：

```text
total: 30
equivalent: 30
different: 0
```

RAG 指标不低于 v0.8 baseline；差分不允许出现 capability 名称、输入、Evidence ID、StopReason 和最终答案语义差异。

- [x] **步骤 4：明确真实 provider 只做边界验证。**

离线测试必须在 `/tmp` 执行并显式设置 prompt template 目录，避免根目录 `.env` 污染 fake 回归。真实 provider 验证只运行已有 opt-in Smoke Eval，记录 provider、model、prompt、语料和 commit，不把 provider 不可用写成离线能力迁移失败。

- [x] **步骤 5：用户授权后统一收尾提交验证补强。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

### 任务 9：发布 v0.9 架构版本并同步事实源

**状态：已完成（当前事实源已同步，未提交）。**

**文件：**
- 创建：`docs/architecture/versions/v0.9-direct-knowledge-capability.md`
- 修改：`TECH_ARCHITECTURE_MVP.md`
- 修改：`docs/architecture.md`
- 修改：`docs/architecture/02-agent-runtime.md`
- 修改：`docs/architecture/04-tools-models.md`
- 修改：`docs/architecture/05-data-observability.md`
- 修改：`docs/architecture/99-changelog.md`

- [x] **步骤 1：先写文档一致性测试或静态检查。**

检查命令：

```bash
rg -n "PolicyRAGTool|search_policy|documents|ToolExecutorCapabilityGateway" \
  docs/architecture/02-agent-runtime.md \
  docs/architecture/04-tools-models.md \
  docs/architecture/05-data-observability.md
```

预期：FAIL；当前主题分册仍描述 v0.8 兼容路径。

- [x] **步骤 2：创建完整 v0.9 版本正文。**

新版本必须包含：

```text
版本信息
基线版本 v0.8
变更原因
完整分层架构
CapabilityCall -> CapabilityRequest -> CapabilityGateway -> KnowledgeGateway 数据流
knowledge.search 与 payment.calculate 注册和权限
EvidenceItem 与 CapabilityResult.output 契约
幂等、超时、错误和 trace
Native/LangGraph 复用边界
相对 v0.8 差异
兼容性与迁移策略：明确内部破坏性升级，无旧符号兼容
任务计划入口
验收标准
已知限制
```

- [x] **步骤 3：同步当前主题文档和版本入口。**

`TECH_ARCHITECTURE_MVP.md` 与 `docs/architecture.md` 只在实现、测试和对抗性审查全部通过后指向 v0.9。主题文档改成当前规则；v0.8 版本正文只保留历史原文，不回写删除内容。

- [x] **步骤 4：运行文档静态校验。**

运行：

```bash
git diff --check
rg -n "PolicyRAGTool|search_policy|ToolExecutorCapabilityGateway|documents" \
  docs/architecture/02-agent-runtime.md \
  docs/architecture/04-tools-models.md \
  docs/architecture/05-data-observability.md \
  docs/architecture/versions/v0.9-direct-knowledge-capability.md
```

预期：第一条返回 0；第二条无输出。`v0.8` 历史版本允许保留这些词作为历史事实。

- [x] **步骤 5：用户授权后统一收尾提交架构版本。**

```bash
# 用户确认后由收尾流程统一暂存；当前不执行。
# 用户确认后由收尾流程统一提交；当前不执行。
```

---

## 4. 任务依赖图

```text
任务 1 协议冻结
  ├──> 任务 2 CapabilityRegistry
  │      └──> 任务 3 DefaultCapabilityGateway
  │             └──> 任务 4 knowledge.search 组合根
  │                    └──> 任务 5 Agent/Runtime 迁移
  │                           └──> 任务 6 答案/CLI/TUI 迁移
  │                                  └──> 任务 7 删除旧实现和静态引用
  │                                         └──> 任务 8 负向、RAG、差分验证
  │                                                └──> 任务 9 v0.9 架构发布
  └──────────────────────────────────────────────────────────────────────> reviewer/tester 对抗性审查
```

### 并行边界

- 任务 2 的注册表单元测试可以与任务 1 的协议测试并行设计，但合并必须先完成任务 1 的字段命名。
- 任务 4 的 KnowledgeGateway 负向用例可以与任务 3 的网关错误语义测试并行编写。
- 任务 9 只能在任务 8 和两轮对抗性审查通过后执行，避免事实源提前宣称 v0.9 已生效。

---

## 5. 全局验收标准

### 5.1 代码和协议

- `ananhu_agent` 和 `tests` 的 Python 代码中零命中：
  - `PolicyRAGTool`
  - `search_policy`
  - `ToolCallRequest`
  - `ToolCallResult`
  - `ToolExecutor`
  - `ToolRegistry`
  - `ToolDefinition`
  - `tool_call_result`
  - `tool_calls`
  - `tool_name`
  - `output["documents"]`、`output.get("documents")` 或 `"documents":` 能力结果投影
  - `from_payload`
  - `to_tool_payload`
- 只存在 `knowledge.search`、`payment.calculate` 两个当前能力名。
- Agent 只能生成 `CapabilityCall`；Agent、KnowledgeGateway 和底层 handler 之间不存在直连调用。
- `CapabilityResult.output` 是唯一能力业务结果来源，失败使用 `CapabilityResult.error`。

### 5.2 知识安全和答案链路

- `KnowledgeQuery` 只由 `knowledge.search` handler 显式构造。
- trusted jurisdiction 优先于模型抽取地区。
- approved、official、audience、effective_at、document_version 过滤在 lexical 召回前执行。
- `EvidenceItem.evidence_id`、版本、来源 URL、hash 和 citation 能一路进入 `WorkflowState.evidence` 和最终答案。
- 无可信地区、无结果、过期、未审核或地区不匹配时不得生成政策承诺。
- 只提供测算而没有政策证据时继续走保守答案。

### 5.3 治理和可观测性

- 非法 capability、非法 caller、缺输入、超时、handler 异常和输出 schema 错误都返回稳定错误码。
- capability started/finished/failed trace 具备 `run_id`、`request_id`、`session_id`、`node_id`、`logical_call_id`、`attempt`。
- 同一 `run_id + logical_call_id` 重试只执行一次，重试结果标记 `reused=true`。
- 不新增第二套状态机、第二套 reducer 或第二套 trace recorder。
- LangGraph 仅调度项目阶段，不把 graph state、message、Command 或 ToolNode 类型带入能力协议。

### 5.4 回归和交付

- `uv run pytest -q` 全部通过。
- KnowledgeGateway、语料质量、RAG eval 专项全部通过。
- 离线 Native/LangGraph differential eval 为 `30/30 equivalent`、`0 different`。
- `git diff --check` 无输出。
- v0.9 版本正文、主题分册、版本入口和 changelog 口径一致。
- v0.8 历史版本正文未被原地改写。

---

## 6. 对抗性 Reviewer 审查计划

审查时使用 `pm-workflow:picky-reviewer`。Reviewer 不负责提出“看起来合理”的认可意见，必须主动寻找可以让计划或实现失效的最小反例。审查发生两轮：

1. 任务 3 完成后：检查新能力网关是否变成了旧 ToolExecutor 的换名包装。
2. 任务 8 完成后：检查最终实现是否真正删除兼容逻辑并覆盖业务闭环。

### 6.1 Reviewer 检查问题

#### 目标覆盖

- 是否同时覆盖协议、网关、KnowledgeGateway、Agent、Runtime、答案、CLI/TUI、测试和架构文档？
- 是否把“直接改造”落实为删除旧符号，而不是增加一层别名？
- 是否明确 KnowledgeGateway 仍必须经过 CapabilityGateway？

#### 兼容层残留

- `PolicyRAGTool` 是否仍能注册、调用、出现在状态、trace、CLI 或测试？
- 是否存在 `search_policy()`、`from_payload()`、`to_tool_payload()`、`documents` 双写或读取 fallback？
- 是否为了让旧测试通过保留 `tool_calls`、`tool_name`、`ToolCallResult` 或 `tool_call_result`？
- 是否通过 `getattr`、`dict.get`、异常捕获或字符串映射偷偷接受旧请求？

#### 过度设计

- `CapabilityCall` 是否只是必要的 Agent 意图协议，还是引入了不需要的多层 Command/Intent/Plan 对象？
- `CapabilityRegistry` 是否只是显式白名单，还是演变成动态插件平台？
- 是否重复实现了 reducer、trace recorder、权限校验或幂等缓存？
- 是否为了保留旧工具而引入 `CompositeCapabilityGateway` 的无意义层级？

#### 边界和安全

- Agent 是否可以绕过 `CapabilityGateway` 直接调用 `KnowledgeGateway` 或 payment handler？
- trusted jurisdiction 是否由模型输入覆盖？
- 无结果、过期、未审核、非法 caller 和未知 capability 是否都能被确定性阻断？
- `EvidenceItem` 是否仍是最终引用链路的事实来源？

#### 任务粒度与验收

- 每个任务是否能独立运行失败测试、最小实现和通过验证？
- 是否有任务依赖未定义的类型、函数或文件？
- 是否存在“补充测试”“适当处理错误”一类无法执行的描述？
- 是否在实现阶段前错误地修改了当前版本入口或 v0.8 历史正文？

### 6.2 Reviewer 输出格式

```text
DECISION: APPROVE|REVISE
CORE_JUDGMENT:
GOAL_COVERAGE_RISKS:
ACCEPTANCE_COVERAGE_RISKS:
TASK_COVERAGE_RISKS:
SIMPLIFICATION_RISKS:
QUESTIONS:
SIMPLIFICATIONS:
VERDICT:
```

### 6.3 Reviewer 通过门禁

- `DECISION` 必须为 `APPROVE`。
- `SIMPLIFICATION_RISKS` 不得为空；Reviewer 必须明确检查过是否能删除一层抽象。
- 不得存在未关闭的“旧兼容符号残留”“Agent 直连能力”“双 reducer”“双 trace”问题。
- 若 `DECISION=REVISE`，先修计划或实现，再重新运行对应轮次审查；不得用口头解释替代修订和验证。

---

## 7. 对抗性 Tester 审查计划

审查时使用 `pm-workflow:picky-tester`。Tester 只接受可以复现的命令、断言、静态扫描或 artifact，不接受“代码看起来覆盖了”的证据。Tester 也必须审查失败路径和相邻待遇测算路径，不能只验证政策正向命中。

### 7.1 Tester 必测矩阵

| 风险 | 黑盒输入或动作 | 必须观察的证据 |
|---|---|---|
| 无可信地区 | 用户提到地方政策但 `trusted_jurisdiction={}` | `no_trusted_jurisdiction_match`、无 Evidence、保守答案 |
| 模型伪造地区 | payload 同时含 `trusted_jurisdiction={"province":"四川省"}` 和 `province="辽宁省"` | 实际 KnowledgeQuery 仍为四川省 |
| 无结果 | 查询不存在的条款 | `evidences=[]`、`no_result_reason` 非空、不得编造 |
| 过期文档 | `effective_at` 晚于文档失效日期 | 过期文档不进入结果 |
| 未审核文档 | corpus 中存在 `review_status != approved` | 未审核文档不进入结果 |
| 非法 capability | 请求 `PolicyRAGTool` | `capability_not_registered` |
| 非法 caller | `PaymentCalculationAgent` 调用 `knowledge.search` | `caller_not_allowed` |
| 缺输入 | 缺少 `query` 或 `trusted_jurisdiction` | `invalid_input_schema` |
| 超时 | handler 睡眠超过 timeout | `capability_timeout`、failed trace |
| Handler 错误 | handler 抛异常 | 稳定错误码、无底层异常泄漏 |
| 重试/幂等 | 同一 logical_call_id，attempt 1/2 | 只执行一次、第二次 `reused=true` |
| 测算相邻路径 | `payment.calculate` 合法和缺输入 | 结果正确、错误分类正确 |
| 双运行时 | `eval --runtime both` | 30/30 equivalent、0 different |
| 引用链路 | 有 Evidence 的政策咨询 | Evidence ID、版本、来源和 citation 出现在状态/答案 |
| 旧符号扫描 | 扫描 Python 源码和测试 | 旧符号零命中 |

### 7.2 Tester 命令清单

```bash
uv run pytest tests/test_direct_capability_migration.py -v
uv run pytest tests/test_capability_registry.py tests/test_default_capability_gateway.py -v
uv run pytest tests/test_knowledge_gateway_contract.py tests/test_policy_corpus_quality.py tests/test_rag_eval.py -v
uv run pytest tests/test_business_agents.py tests/test_workflow_reducer.py tests/test_workflow_contracts.py -v
uv run pytest tests/test_answer_governance.py tests/test_answer_governance_extended.py -v
uv run pytest tests/runtime_contracts -v
uv run pytest -q
git diff --check
if rg -n "PolicyRAGTool|search_policy|ToolCallRequest|ToolCallResult|ToolExecutor|ToolRegistry|ToolDefinition|tool_call_result|tool_calls|tool_name|output(\.get)?\(['\"]documents['\"]\)|['\"]documents['\"]\s*:|\bfrom_payload\b|\bto_tool_payload\b" ananhu_agent tests; then exit 1; fi
```

离线双运行时命令必须从 `/tmp` 执行：

```bash
ROOT="$(git rev-parse --show-toplevel)"
cd /tmp
ANANHU_PROMPT_TEMPLATE_DIR="$ROOT/ananhu_agent/prompts/templates" \
ANANHU_RUNTIME_DIR=/tmp/ananhu-verify-runtime-v09 \
uv run --project "$ROOT" ananhu-agent eval \
  "$ROOT/data/eval/eval_cases.jsonl" \
  --runtime both
```

### 7.3 Tester 输出格式

```text
DECISION: APPROVE|REVISE
CORE_JUDGMENT:
COVERAGE_GAPS:
EVIDENCE_GAPS:
REGRESSION_GAPS:
REQUIRED_TESTS:
VERDICT:
```

### 7.4 Tester 通过门禁

- 每条全局验收标准都能映射到至少一条命令和一个具体断言或扫描结果。
- 正向、负向、异常、重试、权限、相邻测算和双运行时路径均有证据。
- 静态扫描不豁免 Python 代码、测试、README、AGENTS、后端规范、当前主题文档、当前 Prompt 或 v0.9 版本正文；只豁免 `docs/architecture/99-changelog.md`、`docs/architecture/versions/v0.8-*.md` 及更早版本正文、旧计划文件中的历史记录。
- `DECISION` 必须为 `APPROVE`；否则修复测试缺口或实现缺陷后重新执行完整命令集。

---

## 8. 停止条件、风险和迁移边界

### 8.1 必须停止并让用户确认的情况

- 发现主分支或集成分支在本任务期间出现与本计划冲突的并发改动。
- Native 与 LangGraph 业务结果不等价，且原因不能归结为允许的 runtime 身份、时间或延迟差异。
- 需要修改 v0.8 历史版本正文才能让测试通过。
- 发现外部调用方依赖旧工具名，但仓库内没有可审计的迁移范围。
- 需要保留旧符号才能维持现有用户数据恢复，而当前没有版本化迁移策略。

### 8.2 主要风险与控制

| 风险 | 控制 |
|---|---|
| 大范围重命名遗漏 | 任务 1 冻结新协议，任务 7 做零命中扫描，全量测试负责发现动态遗漏 |
| 新网关只是旧适配器换名 | 任务 3 reviewer 强制检查直接 handler、无 ToolExecutor import 和 capability trace |
| Evidence 在聚合阶段丢失 | 任务 6 对 `evidence_id`、citation、版本和 source URL 做端到端断言 |
| trusted jurisdiction 被模型覆盖 | 任务 4 加 RecordingKnowledgeGateway 和冲突地区测试 |
| 测算路径回归 | 任务 5/8 单独验证 `payment.calculate` 成功、缺输入、权限和结果字段 |
| 运行时分叉 | 任务 5/8 使用同一阶段服务和双运行时 differential eval |
| 文档口径提前切换 | 任务 9 作为最后任务，v0.8 历史正文只读 |

### 8.3 真实 provider 验证边界

本计划的通过条件是离线 fake model、离线 lexical corpus、能力契约和双运行时差分全部通过。真实 provider 只验证：

- 真实模型能按当前 `CapabilityCall` 触发政策和测算路径；
- 真实 provider 失败仍被 `CapabilityGateway` 和 Runtime 归一为项目错误；
- 真实 provider 不得决定 jurisdiction、权限、Evidence 有效性或能力名称。

真实 provider smoke 的结果单独记录，不替代离线确定性测试，也不允许因为本机 `.env` 存在而改变离线验证命令的行为。

---

## 9. 执行顺序与完成定义

按任务 1 至任务 9 顺序执行；任务 3、任务 8 和任务 9 之间分别插入 reviewer/tester 门禁。
任务级 commit 命令只作为拆分建议，不在用户未确认前执行；最终合并前必须提供：

1. 改动范围：旧兼容层删除、新能力协议、知识能力接入、答案链路和测试文件。
2. 验证结果：专项测试、全量测试、静态扫描、`git diff --check` 和离线双运行时结果。
3. 对抗性审查结果：Reviewer 和 Tester 的标准化输出，均为 `APPROVE`。
4. 版本文档结果：v0.9 新版本正文、当前入口更新和 changelog 记录。

计划完成并保存到：

```text
docs/superpowers/plans/2026-07-11-direct-knowledge-capability-v0.9.md
```

本计划阶段只创建任务分支和计划文档，不提交、不推送、不合并；实现分支完成后仍按项目规范等待用户确认，再执行 commit 和合并。

## 10. 对抗性审查执行记录

### 第一轮

- Reviewer：`REVISE`。发现可信地区回退、空范围返回全国政策、缓存权限绕过、并发幂等竞态、浅层输出校验、旧 `model_called`/`tool_*` 语义和计划提交流程冲突。
- Tester：`REVISE`。要求补齐 handler 异常、嵌套 Evidence、过期/未审核黑盒、payment 负向、TUI 异步异常和当前文档扫描。

### 修订结果

- 缓存前完成注册、caller、输入和请求指纹校验；按 `(run_id, logical_call_id)` 加锁，handler 只执行一次。
- 未注册能力不读写既有缓存；已注册能力变更返回 `logical_call_conflict`。
- `knowledge.search` 输出使用生产 validator 校验 EvidenceItem、`no_result_reason` 和结构字段。
- 空 `trusted_jurisdiction` 不再从用户文本回填，也不扩大到全国政策；CLI 通过显式 `--province/--city` 提供已确认地区。
- 删除旧 `model_called` 双写、旧指标、旧 TUI tool 语义和当前 Prompt 残留；保留 changelog 与历史架构正文中的历史事实。
- TurnWidget 等待挂载并防护子控件尚未就绪，异常路径不再产生未处理异步任务。

### 最终签收

- Reviewer：`APPROVE`。
- Tester：`APPROVE`。
- 全量：`218 passed, 1 skipped`。
- TUI debug + PTY：`36 passed`，无 `Task exception was never retrieved`、`Traceback` 或 `NoMatches`。
- Native/LangGraph：`30/30 equivalent, 0 different`。
- 源码和当前文档旧语义扫描：零命中；`git diff --check`：通过；v0.8 历史正文：未修改。
