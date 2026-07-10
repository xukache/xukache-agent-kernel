# 04. 能力、模型与知识治理

## 范围

本文定义统一能力执行网关、模型适配、政策知识检索、幂等和版本治理。现有类名可以保留，但公共语义必须框架中立。

## 能力分类

| 能力 | 当前实现 | 目标端口 |
|---|---|---|
| 政策检索 | `PolicyRAGTool` | `KnowledgeGateway.search()` |
| 待遇辅助测算 | `PaymentCalculationTool` | `CalculationService.calculate()` |
| 模型调用 | `ModelRouter` + Fake Model | `ModelGateway` / `ModelRegistry` |
| 未来语音/多模态 | 未实现 | `CapabilityGateway` 下的适配器 |

Agent 不直接调用这些实现，只产生项目 `CapabilityRequest`。

## CapabilityRegistry

每项能力至少声明：

- 名称、版本、输入/输出 schema。
- 风险等级和所需权限。
- 支持的 jurisdiction、模态和超时。
- 幂等等级、重试策略和 fallback。
- trace 脱敏策略和用量计量方式。

注册表是显式白名单，不使用运行时任意发现作为默认路径。

## CapabilityGateway

现有 `ToolExecutor` 承担统一执行网关职责。目标链路：

```text
解析 CapabilityRequest
  -> 注册和 schema 校验
  -> tenant / jurisdiction / permission 校验
  -> 稳定幂等键检查
  -> timeout / retry / circuit policy
  -> 执行 adapter
  -> 输出 schema 和证据校验
  -> 脱敏
  -> trace + usage
```

LangGraph ToolNode 或 Agent framework tool 不得绕过该网关。

## CapabilityResult

统一结果至少包含：

```text
status
data
evidence
capability_name
capability_version
input_digest
duration_ms
retryable
error_code
```

禁止仅返回一段自然语言文本并要求下游 Agent 二次解析关键计算字段。

## 幂等与重试

逻辑调用键由 `run_id + node_id + logical_call_id + capability_version` 构成，`attempt` 单独记录。能力声明：

- `read_only_repeatable`：检索类，可在版本一致时重试。
- `deterministic`：计算类，相同输入和版本返回相同结果。
- `side_effecting`：未来写操作，必须持久化幂等记录并限制重放。

框架节点重试不能自行决定是否重复执行业务能力。

## ModelGateway

- 应用层按能力 profile 选择模型，不依赖供应商类。
- 统一结构化输出校验、超时、重试、fallback、token 和错误分类。
- 模型不得决定可信 jurisdiction、权限或政策有效性。
- Fake Model 是 contract test 替身；真实模型实验单独启用和报告。

`ModelRouter` 后续演进为 `ModelGateway/ModelRegistry` 时应保留当前 profile 配置和 trace 兼容性。

## KnowledgeGateway

检索前必须使用可信元数据过滤：

```text
tenant
+ jurisdiction
+ effective_at
+ review_status
+ audience_role
+ source_type
+ document_version
```

目标检索流程：

```text
metadata filter
  -> BM25/lexical
  -> vector retrieval
  -> fusion
  -> reranker
  -> citation validator
```

向量检索只是候选召回方式。TopK 和阈值必须由 eval 数据校准，不能作为未经验证的常量宣称正确。

## EvidenceItem

政策证据至少包含：

- 文档 ID、标题、条款和原文片段。
- jurisdiction、效力层级、生效/失效时间。
- review status、document version、source URL。
- 召回渠道、原始分数、融合/重排分数。
- 证据 hash 和语料版本。

答案中的结论必须能回指 Evidence ID。资源或证据失败时，不生成承诺“已为你找到”的邀请文案。

## 待遇辅助测算

测算结果记录输入及来源、地区、基数年份、公式版本、舍入规则、不确定项和风险提示。模型只能解释结果，不能替代确定性计算，也不能把辅助测算包装成最终待遇承诺。
