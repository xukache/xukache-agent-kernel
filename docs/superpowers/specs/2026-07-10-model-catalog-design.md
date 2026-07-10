# 多 Provider 模型目录设计定稿

## 状态

- 日期：2026-07-10
- 状态：设计定稿，等待后续实现计划
- 基线：MVP v0.5 `ModelGateway` 与 OpenAI-compatible provider
- 目标任务：任务 33，模型目录与按 Agent/Profile 路由

## 背景

任务 32 已经完成框架中立 `ModelGateway`，并接入通用 OpenAI-compatible
`/chat/completions` adapter。当前配置能支持一个 OpenAI-compatible provider，但当后续出现多个
模型提供商、多个模型档位、不同 Agent 使用不同模型时，单层环境变量会变得难维护。

本设计只定稿配置与路由边界，不引入 Anthropic、Gemini 等原生 SDK。后续如果需要原生 provider，
只新增 provider adapter，不改变 Agent、Prompt 和 Runtime 的公共协议。

## 设计目标

1. 支持多个 OpenAI-compatible 提供商，例如 DeepSeek、通义千问、OpenAI-compatible 私有网关。
2. 支持不同 Agent、Prompt 或阶段选择不同模型档位，例如 `intent_fast`、`compose_quality`。
3. API key 不进入模型 profile、trace、测试 fixture、artifact 或 Git。
4. Agent 不知道 provider、base URL、API key 或 SDK 类型，只使用项目定义的 `model_profile`。
5. Native Runtime 和 LangGraph Runtime 继续复用同一个 `ModelGateway` 装配入口。
6. 默认仍可离线运行 Fake gateway，未显式启用真实模型时 CI 不访问网络。

## 非目标

1. 不实现自动 fallback。fallback 需要单独设计质量、成本和可观测语义。
2. 不实现 provider 级负载均衡、熔断、配额池或动态路由。
3. 不在 Agent 内增加模型选择逻辑。
4. 不把真实模型 smoke 结果并入离线 eval 质量指标。
5. 不在本任务引入 HTTP API、WebSocket 或前端配置界面。

## 推荐方案

采用两层模型目录：

- `providers`：描述接入协议、base URL、API key 环境变量名、可选组织/租户参数。
- `profiles`：描述业务可选择的模型档位，引用 provider，并设置 model、temperature、timeout 和可选价格。

示例：

```yaml
providers:
  deepseek:
    protocol: openai_compatible
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY

  qwen:
    protocol: openai_compatible
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key_env: QWEN_API_KEY

profiles:
  intent_fast:
    provider: deepseek
    model: deepseek-chat
    temperature: 0
    timeout_seconds: 20

  compose_quality:
    provider: qwen
    model: qwen-plus
    temperature: 0.2
    timeout_seconds: 45
```

环境变量只保存密钥：

```bash
DEEPSEEK_API_KEY=
QWEN_API_KEY=
ANANHU_MODEL_CATALOG=config/models.yaml
ANANHU_REAL_MODEL_SMOKE=0
```

## 配置文件位置

默认读取 `config/models.yaml`。如需覆盖路径，使用 `ANANHU_MODEL_CATALOG`。

仓库可以提交不含密钥的 `config/models.example.yaml`，本地 `config/models.yaml` 应加入
`.gitignore` 或只提交无敏感信息的默认 Fake 配置。API key 只能通过环境变量解析。

## 路由规则

`PromptManager` 或阶段配置只声明 `model_profile`：

```yaml
agent_profiles:
  intent:
    model_profile: intent_fast
  compose:
    model_profile: compose_quality
```

运行时装配流程：

```text
RuntimeSettings
  -> ModelCatalogLoader
  -> ProviderConfig + ModelProfile
  -> ModelRouter
  -> ModelGateway.generate_structured()
```

Agent 的输入输出协议不新增 provider 字段。Agent 只拿到 PromptManager 渲染后的请求，模型选择由阶段服务
或组合根注入，避免业务 Agent 直接依赖基础设施配置。

## 校验规则

启动时校验：

1. `profiles.*.provider` 必须引用已存在 provider。
2. `providers.*.protocol` 当前只允许 `openai_compatible`。
3. `api_key_env` 只能是环境变量名，不能是密钥值。
4. `base_url` 必须是 `https://` URL；本地测试允许通过专用测试配置覆盖。
5. `temperature` 范围为 `0 <= value <= 2`。
6. `timeout_seconds` 必须大于 0。
7. 价格字段缺失时不估算费用，但 token usage 仍正常记录。

运行时校验：

1. profile 不存在时返回配置类 `ModelGatewayError`。
2. provider key 未设置且请求真实模型时返回配置类错误，不静默降级到 Fake。
3. Fake 与真实 provider 的 usage 必须用 `usage_source` 区分。

## Trace 与安全

模型 trace 允许记录：

- profile
- provider 名称
- provider protocol
- model
- finish reason
- latency
- token usage
- cost estimate
- logical call ID

模型 trace 禁止记录：

- API key
- `api_key_env` 对应的值
- 完整 Authorization header
- 未脱敏 provider 错误响应体
- 包含用户隐私的完整 prompt 原文，除非已有 trace 脱敏策略覆盖

## 测试策略

1. `ModelCatalogLoader` 单元测试覆盖 YAML 解析、provider/profile 引用、非法协议、非法 URL、非法温度和缺失 key。
2. `ModelRouter` 测试覆盖按 profile 找到 provider，并继续调用同一个 `ModelGateway` 端口。
3. Native/LangGraph 差分测试保持 Fake 默认路径，确保新增目录不破坏离线确定性。
4. OpenAI-compatible adapter 使用受控 HTTP transport 做 contract test。
5. 真实 smoke 仍由 `ANANHU_REAL_MODEL_SMOKE=1` 显式开启，无 key 时 skip。

## 迁移策略

第一阶段兼容现有任务 32 环境变量：

- `ANANHU_MODEL_BASE_URL`
- `ANANHU_MODEL_API_KEY`
- `ANANHU_MODELS`

当 `ANANHU_MODEL_CATALOG` 存在时优先使用模型目录；不存在时回退到旧配置。完成一次版本迁移后，再决定是否废弃
`ANANHU_MODELS` JSON 环境变量。

## 验收标准

1. 可以在一个配置文件中声明至少两个 OpenAI-compatible provider。
2. 可以声明至少两个 profile，并分别路由到不同 provider。
3. Agent、domain、application 公共协议不暴露 provider SDK、base URL 或 API key。
4. 默认测试不访问网络。
5. 缺失 key、未知 profile、未知 provider 和 schema 错误都有明确错误分类。
6. trace 与 RunReport 能区分 profile、provider、model、usage source 和费用估算来源。

## 后续实现边界

后续实现需要新建任务分支，并按项目规则升级架构版本到 v0.6，因为模型目录会改变配置模型、组合根和
模型路由边界。实现前应新增 `docs/architecture/versions/v0.6-model-catalog.md`，同步更新
`TECH_ARCHITECTURE_MVP.md`、`docs/architecture.md`、`docs/architecture/04-tools-models.md` 和
`docs/architecture/99-changelog.md`。
