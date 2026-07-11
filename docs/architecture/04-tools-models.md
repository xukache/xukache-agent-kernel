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

Agent 不直接调用这些实现，只产生项目 `CapabilityRequest`。当前能力协议位于 `ananhu_agent/capabilities/`，通过 `ToolExecutorCapabilityGateway` 适配现有 `ToolExecutor`。

## CapabilityRegistry

每项能力至少声明：

- 名称、版本、输入/输出 schema。
- 风险等级和所需权限。
- 支持的 jurisdiction、模态和超时。
- 幂等等级、重试策略和 fallback。
- trace 脱敏策略和用量计量方式。

注册表是显式白名单，不使用运行时任意发现作为默认路径。

## CapabilityGateway

`CapabilityGateway` 是 Runtime/阶段服务依赖的能力端口，`ToolExecutorCapabilityGateway` 包装现有 `ToolExecutor` 并保留原有治理行为。当前链路：

```text
解析 CapabilityRequest
  -> 注册和 schema 校验
  -> caller permission 校验
  -> 稳定幂等键检查
  -> ToolExecutor adapter
  -> timeout
  -> 输出 schema 校验
  -> trace
```

LangGraph ToolNode 或 Agent framework tool 不得绕过该网关。

## CapabilityResult

统一结果至少包含：

```text
status
output
capability_name
caller
node_id
runtime_name
runtime_version
logical_call_id
attempt
policy
error
tool_call_result
```

禁止仅返回一段自然语言文本并要求下游 Agent 二次解析关键计算字段。

## 幂等与重试

逻辑调用键由 `run_id + node_id + logical_call_id + capability_version` 构成，`attempt` 单独记录。当前 MVP 适配器以 `logical_call_id` 复用同一进程内历史结果，避免同一逻辑调用被 ToolExecutor 判为不可解释的重复执行。能力声明：

- `read_only_repeatable`：检索类，可在版本一致时重试。
- `deterministic`：计算类，相同输入和版本返回相同结果。
- `side_effecting`：未来写操作，必须持久化幂等记录并限制重放。

框架节点重试不能自行决定是否重复执行业务能力。`CapabilityRequest` 同时携带项目运行时名称和版本，适配器仅将其写入 ToolExecutor trace，不把框架类型传入能力协议。

## ModelGateway

- 应用层按能力 profile 选择模型，不依赖供应商类。
- 统一结构化输出校验、超时、重试、fallback、token 和错误分类。
- 模型不得决定可信 jurisdiction、权限或政策有效性。
- Fake Model 是 contract test 替身；真实模型实验单独启用和报告。

当前公共端口使用项目定义的 async `ModelGateway.generate_structured()`，输入输出为
`ModelRequest`、`ModelResult` 和 `ModelGatewayError`，不得暴露 provider SDK、LangGraph message
或 HTTP 响应类型。Native 与 LangGraph Runtime 通过同一组合根复用 gateway。

默认 `FakeModelGateway` 保持离线回归确定性。真实适配器实现 OpenAI-compatible
`/chat/completions` 最小子集，profile 使用 `provider=openai_compatible`；API key、base URL 和
显式 smoke 开关由环境配置提供，不写入 profile、trace 或 artifact。无 key 的常规测试必须 skip。
`RuntimeSettings` 自动读取项目当前工作目录的 UTF-8 `.env`；已导出的 shell 环境变量优先于 `.env`，
部署环境可以覆盖本地配置而无需修改文件。

模型目录使用 `providers + profiles` 两层结构。`providers` 保存 OpenAI-compatible 协议、base URL 和
API key 环境变量名；`profiles` 保存业务模型档位并引用 provider。Prompt metadata 和阶段服务只选择
`model_profile`，Agent 不感知 provider、URL 或密钥。

结构化调用至少记录 Prompt 引用、profile、provider、model、finish reason、attempt、延迟、输入/
输出/cache/total token 和可选费用估算。配置、鉴权、限流、超时、provider、响应格式和 schema
错误使用项目错误码归一化。`ModelRouter` 只保留 profile registry/组合职责，不再向 Agent 暴露具体客户端。

OpenAI-compatible `json_object` 调用由 Gateway 统一向消息附加英文 `JSON` 约束和项目
`output_schema`，兼容要求消息显式包含 JSON 关键字的 provider；响应仍须由项目 JSON Schema
校验，不能仅依赖模型遵循提示。

### ObservableModelGateway 与 Reasoning

组合根在具体 gateway 外装配 `ObservableModelGateway`，集中发布 model started/finished/failed。装饰器
只在收到完整 `ModelRequest` 后发布真实输入视图，完成后发布结构化输出、Usage、耗时和瞬态 reasoning；
Agent 不依赖 RunEventSink，阶段内旧的重复模型埋点必须移除。

OpenAI-compatible adapter 只接受字符串类型的 `message.reasoning_content`；未返回、null 或空字符串
归一为 `None`，其他类型归类为 provider 响应格式错误。`ModelResult.reasoning_content` 必须设置
`exclude=True, repr=False`。实时公共投影只记录 `reasoning_available`、原始字符数和裁剪状态，裁剪
脱敏后的原文仅存在于当前进程瞬态 payload，不能进入 trace、状态、报告、badcase 或 eval。

### Usage Reported 语义

`ModelUsage.reported` 区分 provider 明确报告的零值与未报告 usage。单轮 token 只聚合成功且
`reported=True` 的 ModelResult；任一成功 provider 调用未报告时合计为 `tokens unknown` 且速度为 `--`。
Fake 固定为 `reported=False, usage_source=fake`，纯 Fake 轮次显示 `fake · 0 tokens`。失败且无
ModelResult 的尝试不计 token；provider total 与分项不一致时保留原值并标记 inconsistent。Textual
单轮 usage 行在完整 provider usage 可用时展示 `in`、`out`、可选 `cache`、`Σ total` 和输出速度；
`cache` 是 provider 单独报告的缓存命中字段，不参与替代 input/output/total 的含义。

## 实时 Capability 事件

`CapabilityRequest` 必须携带 `run_id`。CapabilityGateway 在既有权限、schema、幂等、重试和超时治理
边界内发布 started/finished/failed，payload 只包含治理后的实际参数、结果、fallback 和耗时。ToolExecutor
或 LangGraph ToolNode 不得绕过网关，也不得自行发布缺失 run 身份的事件。

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
