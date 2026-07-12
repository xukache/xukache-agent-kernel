# 多 Provider 模型目录实现计划

> **执行状态（2026-07-12）：已替代，只读，不可执行。**
>
> 本文原计划未按复选框逐项执行；模型目录能力已由 v0.6 架构和代码事实源落地，相关提交为
> `246f592`、`60e4066`。后续不要根据本文创建任务分支。
> 正文中的未勾选步骤是原计划未按原路径执行的历史记录，不是当前待办。
>
> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 `providers + profiles` 两层模型目录，让不同 Agent/Prompt 可以通过 `model_profile` 路由到不同 OpenAI-compatible provider。

**架构：** 在现有 v0.5 `ModelGateway` 之上新增 `ModelCatalog` 配置层。`RuntimeSettings` 只负责定位目录文件和保留旧环境变量兼容；`ModelRouter` 从目录解析后的 profile 装配 `FakeModelGateway` 或 `OpenAICompatibleModelGateway`，Agent 和 Runtime 公共协议不暴露 provider、base URL 或 API key。

**技术栈：** Python 3.11、Pydantic v2、pydantic-settings、PyYAML、httpx MockTransport、pytest、uv。

---

## 文件结构

- 创建：`ananhu_agent/config/model_catalog.py`  
  职责：定义 `ProviderConfig`、`ModelProfileConfig`、`ModelCatalog` 和 `load_model_catalog()`，集中处理 YAML 解析、旧环境变量兼容和启动校验。
- 修改：`ananhu_agent/config/settings.py`  
  职责：新增 `model_catalog` 路径配置，继续保留任务 32 的 `model_api_key`、`model_base_url`、`models` 兼容字段。
- 修改：`ananhu_agent/models/model_router.py`  
  职责：改为先读取 `ModelCatalog`，再按 profile 解析 provider 与 secret，继续缓存 gateway。
- 创建：`config/models.example.yaml`  
  职责：提交无密钥的多 provider 示例配置。
- 修改：`.gitignore`  
  职责：忽略本地 `config/models.yaml`，允许提交 `config/models.example.yaml`。
- 修改：`docs/architecture/versions/v0.6-model-catalog.md`  
  职责：发布模型目录架构快照。
- 修改：`TECH_ARCHITECTURE_MVP.md`、`docs/architecture.md`、`docs/architecture/04-tools-models.md`、`docs/architecture/99-changelog.md`  
  职责：同步当前架构入口和主题分册。
- 创建：`tests/test_model_catalog_config.py`  
  职责：覆盖 YAML 解析、校验、secret 解析和旧配置兼容。
- 修改：`tests/test_model_router_config.py`  
  职责：覆盖 router 使用模型目录后的 gateway 装配和错误分类。

## 任务 1：架构版本 v0.6 文档

**文件：**
- 创建：`docs/architecture/versions/v0.6-model-catalog.md`
- 修改：`TECH_ARCHITECTURE_MVP.md`
- 修改：`docs/architecture.md`
- 修改：`docs/architecture/04-tools-models.md`
- 修改：`docs/architecture/99-changelog.md`

- [ ] **步骤 1：从 v0.5 复制新版本正文**

运行：

```bash
cp docs/architecture/versions/v0.5-real-model-gateway.md docs/architecture/versions/v0.6-model-catalog.md
```

预期：生成 `docs/architecture/versions/v0.6-model-catalog.md`。

- [ ] **步骤 2：编辑 v0.6 正文**

将 `docs/architecture/versions/v0.6-model-catalog.md` 调整为完整自洽版本，至少包含以下段落：

```markdown
# 安安虎工伤智能助手 Agent Harness 技术架构（MVP v0.6）

## 版本信息

| 字段 | 内容 |
|---|---|
| 状态 | 当前有效架构 |
| 版本 | v0.6 |
| 发布日期 | 2026-07-10 |
| 基线版本 | v0.5-real-model-gateway |
| 变更原因 | 在 OpenAI-compatible ModelGateway 基础上引入 providers + profiles 两层模型目录，支持多 provider 和按 Agent/Profile 路由。 |

## Provider/Profile 模型目录

模型配置拆为两层：

- `providers` 描述协议、base URL 和 API key 环境变量名。
- `profiles` 描述业务可选择的模型档位，引用 provider，并声明 model、temperature、timeout 和可选价格。

Agent、Prompt、Runtime 公共协议只使用 `model_profile`。provider 名称、base URL、API key 和 SDK 类型不得进入 domain、application、Agent 或 Runtime 公共协议。

## 配置优先级

`ANANHU_MODEL_CATALOG` 指向 YAML 模型目录时优先使用目录；未配置目录时兼容 v0.5 的 `ANANHU_MODELS`、`ANANHU_MODEL_API_KEY` 和 `ANANHU_MODEL_BASE_URL`。
```

预期：文档明确 v0.6 是当前模型目录架构，且不是只记录差异。

- [ ] **步骤 3：更新入口文档**

将 `TECH_ARCHITECTURE_MVP.md` 当前版本指向改为：

```markdown
> 当前有效版本：[`v0.6-model-catalog.md`](docs/architecture/versions/v0.6-model-catalog.md)
```

将当前版本表更新为：

```markdown
| 架构版本 | v0.6 |
| 发布日期 | 2026-07-10 |
| 基线 | v0.5 Real ModelGateway |
| 技术路线 | 框架中立业务内核 + 双运行时共享 ModelGateway + Provider/Profile 模型目录 |
| 完整正文 | `docs/architecture/versions/v0.6-model-catalog.md` |
```

在版本索引顶部新增：

```markdown
| v0.6 | 当前有效 | `docs/architecture/versions/v0.6-model-catalog.md` | Provider/Profile 模型目录与按模型档位路由 |
```

并将 v0.5 状态改为 `已归档`。

- [ ] **步骤 4：更新主题分册**

在 `docs/architecture/04-tools-models.md` 的 `ModelGateway` 小节追加：

```markdown
模型目录使用 `providers + profiles` 两层结构。`providers` 保存 OpenAI-compatible 协议、base URL 和
API key 环境变量名；`profiles` 保存业务模型档位并引用 provider。Prompt metadata 和阶段服务只选择
`model_profile`，Agent 不感知 provider、URL 或密钥。
```

在 `docs/architecture/99-changelog.md` 顶部追加：

```markdown
## v0.6 - 2026-07-10

- 引入 Provider/Profile 两层模型目录，支持多个 OpenAI-compatible provider 和按模型档位路由。
- 保留 v0.5 环境变量兼容路径；默认 Fake 模型和离线 eval 行为不变。
- API key 继续只通过环境变量读取，禁止进入 profile、trace、测试 fixture 或 artifact。
```

- [ ] **步骤 5：运行文档差异检查**

运行：

```bash
git diff -- docs/architecture/versions/v0.6-model-catalog.md TECH_ARCHITECTURE_MVP.md docs/architecture.md docs/architecture/04-tools-models.md docs/architecture/99-changelog.md
```

预期：只包含 v0.6 模型目录相关文档变更。

- [ ] **步骤 6：Commit**

运行：

```bash
git add docs/architecture/versions/v0.6-model-catalog.md TECH_ARCHITECTURE_MVP.md docs/architecture.md docs/architecture/04-tools-models.md docs/architecture/99-changelog.md
git commit -m "docs(architecture): 发布模型目录架构 v0.6"
```

预期：生成架构文档提交。

## 任务 2：ModelCatalog 配置解析与校验

**文件：**
- 创建：`ananhu_agent/config/model_catalog.py`
- 修改：`ananhu_agent/config/settings.py`
- 创建：`tests/test_model_catalog_config.py`

- [ ] **步骤 1：编写失败测试**

创建 `tests/test_model_catalog_config.py`：

```python
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from ananhu_agent.config.model_catalog import load_model_catalog
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.ports.model_gateway import ModelErrorCode, ModelGatewayError


def test_loads_catalog_from_yaml_and_resolves_provider_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_path = tmp_path / "models.yaml"
    catalog_path.write_text(
        """
providers:
  deepseek:
    protocol: openai_compatible
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
profiles:
  intent_fast:
    provider: deepseek
    model: deepseek-chat
    temperature: 0
    timeout_seconds: 20
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-from-env")

    catalog = load_model_catalog(RuntimeSettings(model_catalog=catalog_path))

    profile = catalog.profile("intent_fast")
    provider = catalog.provider_for_profile("intent_fast")
    assert profile.model == "deepseek-chat"
    assert provider.name == "deepseek"
    assert provider.api_key.get_secret_value() == "secret-from-env"


def test_catalog_rejects_unknown_profile_provider(tmp_path: Path) -> None:
    catalog_path = tmp_path / "models.yaml"
    catalog_path.write_text(
        """
providers: {}
profiles:
  intent_fast:
    provider: missing
    model: deepseek-chat
""",
        encoding="utf-8",
    )

    with pytest.raises(ModelGatewayError) as captured:
        load_model_catalog(RuntimeSettings(model_catalog=catalog_path))

    assert captured.value.code is ModelErrorCode.CONFIGURATION
    assert "unknown provider" in str(captured.value)


def test_catalog_rejects_secret_literal_in_api_key_env(tmp_path: Path) -> None:
    catalog_path = tmp_path / "models.yaml"
    catalog_path.write_text(
        """
providers:
  bad:
    protocol: openai_compatible
    base_url: https://model.example.test/v1
    api_key_env: sk-real-secret-value
profiles:
  intent_fast:
    provider: bad
    model: provider-model
""",
        encoding="utf-8",
    )

    with pytest.raises(ModelGatewayError) as captured:
        load_model_catalog(RuntimeSettings(model_catalog=catalog_path))

    assert captured.value.code is ModelErrorCode.CONFIGURATION


def test_catalog_falls_back_to_legacy_runtime_settings() -> None:
    settings = RuntimeSettings(
        model_api_key=SecretStr("legacy-secret"),
        model_base_url="https://model.example.test/v1",
        models={
            "intent_fast": {
                "provider": "openai_compatible",
                "model": "provider-model",
                "temperature": 0,
                "timeout_seconds": 12,
            }
        },
    )

    catalog = load_model_catalog(settings)

    assert catalog.profile("intent_fast").provider == "legacy_openai_compatible"
    assert catalog.provider_for_profile("intent_fast").api_key.get_secret_value() == "legacy-secret"
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
uv run pytest tests/test_model_catalog_config.py -v
```

预期：FAIL，报错包含 `No module named 'ananhu_agent.config.model_catalog'` 或缺少 `model_catalog` 字段。

- [ ] **步骤 3：新增 RuntimeSettings 字段**

修改 `ananhu_agent/config/settings.py`，在模型相关字段中加入：

```python
    model_catalog: Path | None = None
```

字段保留在 `model_api_key`、`model_base_url`、`models` 附近，注释说明目录优先、旧字段兼容。

- [ ] **步骤 4：实现 ModelCatalog**

创建 `ananhu_agent/config/model_catalog.py`：

```python
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.ports.model_gateway import ModelErrorCode, ModelGatewayError


_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ProviderConfig(BaseModel):
    """模型供应商配置。只保存 secret 引用，不保存 secret 明文。"""

    name: str
    protocol: Literal["fake", "openai_compatible"]
    base_url: str = ""
    api_key_env: str | None = None
    api_key: SecretStr | None = Field(default=None, exclude=True)

    @field_validator("api_key_env")
    @classmethod
    def _validate_api_key_env(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _ENV_NAME_RE.match(value):
            raise ValueError("api_key_env must be an environment variable name")
        return value

    @model_validator(mode="after")
    def _validate_provider(self) -> "ProviderConfig":
        if self.protocol == "openai_compatible" and not self.base_url.startswith("https://"):
            raise ValueError("openai_compatible provider base_url must use https")
        return self


class ModelProfileConfig(BaseModel):
    """业务可选择的模型档位。Agent 只引用 profile 名称。"""

    name: str
    provider: str
    model: str
    temperature: float = Field(default=0, ge=0, le=2)
    timeout_seconds: float = Field(default=30, gt=0)
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    currency: str = "USD"


class ModelCatalog(BaseModel):
    """已校验的模型目录，供 ModelRouter 按 profile 装配 gateway。"""

    providers: dict[str, ProviderConfig]
    profiles: dict[str, ModelProfileConfig]

    def profile(self, name: str) -> ModelProfileConfig:
        try:
            return self.profiles[name]
        except KeyError as exc:
            raise ModelGatewayError(
                ModelErrorCode.CONFIGURATION,
                f"unknown model profile: {name}",
                provider="model_catalog",
                retryable=False,
            ) from exc

    def provider_for_profile(self, profile_name: str) -> ProviderConfig:
        profile = self.profile(profile_name)
        try:
            return self.providers[profile.provider]
        except KeyError as exc:
            raise ModelGatewayError(
                ModelErrorCode.CONFIGURATION,
                f"unknown provider for profile {profile_name}: {profile.provider}",
                provider=profile.provider,
                retryable=False,
            ) from exc


def load_model_catalog(settings: RuntimeSettings) -> ModelCatalog:
    """从 YAML 目录或 v0.5 旧环境变量加载模型目录。"""

    if settings.model_catalog is not None:
        return _load_yaml_catalog(settings.model_catalog)
    return _legacy_catalog(settings)


def _load_yaml_catalog(path: Path) -> ModelCatalog:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ModelGatewayError(
            ModelErrorCode.CONFIGURATION,
            f"cannot read model catalog: {path}",
            provider="model_catalog",
            retryable=False,
        ) from exc

    providers = {
        name: _provider_from_yaml(name, value)
        for name, value in (raw.get("providers") or {}).items()
    }
    profiles = {
        name: ModelProfileConfig(name=name, **(value or {}))
        for name, value in (raw.get("profiles") or {}).items()
    }
    catalog = ModelCatalog(providers=providers, profiles=profiles)
    for profile_name in catalog.profiles:
        catalog.provider_for_profile(profile_name)
    return catalog


def _provider_from_yaml(name: str, value: dict[str, Any]) -> ProviderConfig:
    provider = ProviderConfig(name=name, **(value or {}))
    if provider.api_key_env:
        secret = os.getenv(provider.api_key_env)
        if secret:
            provider = provider.model_copy(update={"api_key": SecretStr(secret)})
    return provider


def _legacy_catalog(settings: RuntimeSettings) -> ModelCatalog:
    providers: dict[str, ProviderConfig] = {
        "fake": ProviderConfig(name="fake", protocol="fake"),
    }
    profiles: dict[str, ModelProfileConfig] = {}

    for name, raw_profile in settings.models.items():
        provider_name = str(raw_profile["provider"])
        if provider_name == "openai_compatible":
            provider_name = "legacy_openai_compatible"
            providers[provider_name] = ProviderConfig(
                name=provider_name,
                protocol="openai_compatible",
                base_url=settings.model_base_url,
                api_key=settings.model_api_key,
            )
        profiles[name] = ModelProfileConfig(
            name=name,
            provider=provider_name,
            model=str(raw_profile["model"]),
            temperature=float(raw_profile.get("temperature", 0)),
            timeout_seconds=float(raw_profile.get("timeout_seconds", 30)),
            input_cost_per_million=raw_profile.get("input_cost_per_million"),
            output_cost_per_million=raw_profile.get("output_cost_per_million"),
            currency=str(raw_profile.get("currency", "USD")),
        )
    return ModelCatalog(providers=providers, profiles=profiles)
```

- [ ] **步骤 5：补齐 Pydantic 错误归一化**

在 `ananhu_agent/config/model_catalog.py` 中导入 `ValidationError`：

```python
from pydantic import ValidationError
```

将 `_load_yaml_catalog()` 中 provider、profile 和 catalog 构造逻辑包裹为：

```python
try:
    providers = {
        name: _provider_from_yaml(name, value)
        for name, value in (raw.get("providers") or {}).items()
    }
    profiles = {
        name: ModelProfileConfig(name=name, **(value or {}))
        for name, value in (raw.get("profiles") or {}).items()
    }
    catalog = ModelCatalog(providers=providers, profiles=profiles)
    for profile_name in catalog.profiles:
        catalog.provider_for_profile(profile_name)
except (TypeError, ValueError, ValidationError, ModelGatewayError) as exc:
    if isinstance(exc, ModelGatewayError):
        raise
    raise ModelGatewayError(
        ModelErrorCode.CONFIGURATION,
        f"invalid model catalog: {exc}",
        provider="model_catalog",
        retryable=False,
    ) from exc

return catalog
```

预期：非法 YAML 内容统一抛出 `ModelGatewayError(CONFIGURATION)`。

- [ ] **步骤 6：运行测试验证通过**

运行：

```bash
uv run pytest tests/test_model_catalog_config.py -v
```

预期：所有 `test_model_catalog_config.py` 测试 PASS。

- [ ] **步骤 7：Commit**

运行：

```bash
git add ananhu_agent/config/settings.py ananhu_agent/config/model_catalog.py tests/test_model_catalog_config.py
git commit -m "feat(model): 增加 Provider Profile 模型目录配置"
```

预期：生成模型目录配置提交。

## 任务 3：ModelRouter 使用模型目录装配 Gateway

**文件：**
- 修改：`ananhu_agent/models/model_router.py`
- 修改：`tests/test_model_router_config.py`

- [ ] **步骤 1：扩展 router 测试**

在 `tests/test_model_router_config.py` 增加：

```python
from pathlib import Path


def test_model_router_builds_openai_gateway_from_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_path = tmp_path / "models.yaml"
    catalog_path.write_text(
        """
providers:
  deepseek:
    protocol: openai_compatible
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
profiles:
  intent_fast:
    provider: deepseek
    model: deepseek-chat
    temperature: 0
    timeout_seconds: 20
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")

    router = ModelRouter(RuntimeSettings(model_catalog=catalog_path))

    assert isinstance(router.gateway_for("intent_fast"), OpenAICompatibleModelGateway)
    assert router.get_profile("intent_fast")["provider"] == "deepseek"


def test_model_router_rejects_catalog_provider_without_secret(tmp_path: Path) -> None:
    catalog_path = tmp_path / "models.yaml"
    catalog_path.write_text(
        """
providers:
  deepseek:
    protocol: openai_compatible
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
profiles:
  intent_fast:
    provider: deepseek
    model: deepseek-chat
""",
        encoding="utf-8",
    )

    router = ModelRouter(RuntimeSettings(model_catalog=catalog_path))

    with pytest.raises(ModelGatewayError) as captured:
        router.gateway_for("intent_fast")

    assert captured.value.code is ModelErrorCode.CONFIGURATION
    assert captured.value.provider == "deepseek"
```

- [ ] **步骤 2：运行 router 测试验证失败**

运行：

```bash
uv run pytest tests/test_model_router_config.py -v
```

预期：新增 catalog 测试 FAIL，因为 `ModelRouter` 尚未调用 `load_model_catalog()`。

- [ ] **步骤 3：改造 ModelRouter**

将 `ananhu_agent/models/model_router.py` 调整为：

```python
from __future__ import annotations

from typing import Any

from ananhu_agent.config.model_catalog import ModelCatalog, load_model_catalog
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.infrastructure.models.fake import FakeModelGateway
from ananhu_agent.infrastructure.models.openai_compatible import OpenAICompatibleModelGateway
from ananhu_agent.ports.model_gateway import (
    ModelErrorCode,
    ModelGateway,
    ModelGatewayError,
)


class ModelRouter:
    """集中管理模型 profile，并装配框架中立 ModelGateway。"""

    def __init__(self, settings: RuntimeSettings | None = None) -> None:
        self.settings = settings or RuntimeSettings()
        self.catalog: ModelCatalog = load_model_catalog(self.settings)
        self._gateways: dict[str, ModelGateway] = {}

    def get_profile(self, profile_name: str) -> dict[str, Any]:
        """返回模型 profile 配置，供 trace 和运行报告记录。"""

        profile = self.catalog.profile(profile_name)
        return profile.model_dump()

    def gateway_for(self, model_profile: str) -> ModelGateway:
        if model_profile in self._gateways:
            return self._gateways[model_profile]

        profile = self.catalog.profile(model_profile)
        provider = self.catalog.provider_for_profile(model_profile)
        if provider.protocol == "fake":
            gateway: ModelGateway = FakeModelGateway()
        elif provider.protocol == "openai_compatible":
            if provider.api_key is None or not provider.base_url:
                raise ModelGatewayError(
                    ModelErrorCode.CONFIGURATION,
                    "OpenAI-compatible provider 缺少 API key 或 base URL",
                    provider=provider.name,
                    retryable=False,
                )
            gateway = OpenAICompatibleModelGateway(
                api_key=provider.api_key.get_secret_value(),
                base_url=provider.base_url,
                model=profile.model,
                temperature=profile.temperature,
                timeout_seconds=profile.timeout_seconds,
                input_cost_per_million=profile.input_cost_per_million,
                output_cost_per_million=profile.output_cost_per_million,
                currency=profile.currency,
            )
        else:
            raise ModelGatewayError(
                ModelErrorCode.CONFIGURATION,
                f"不支持的模型 provider: {provider.protocol}",
                provider=provider.name,
                retryable=False,
            )
        self._gateways[model_profile] = gateway
        return gateway
```

- [ ] **步骤 4：运行 router 测试验证通过**

运行：

```bash
uv run pytest tests/test_model_router_config.py -v
```

预期：所有 router 配置测试 PASS。

- [ ] **步骤 5：运行 model gateway contract 回归**

运行：

```bash
uv run pytest tests/test_model_gateway_contract.py tests/test_model_router_config.py tests/test_model_catalog_config.py -v
```

预期：真实 smoke 未开启时 skip；其余测试 PASS。

- [ ] **步骤 6：Commit**

运行：

```bash
git add ananhu_agent/models/model_router.py tests/test_model_router_config.py
git commit -m "feat(model): 按模型目录装配 gateway"
```

预期：生成 router 集成提交。

## 任务 4：示例配置与本地密钥边界

**文件：**
- 创建：`config/models.example.yaml`
- 修改：`.gitignore`
- 修改：`.env`，仅本地文件，不提交

- [ ] **步骤 1：创建示例配置**

创建 `config/models.example.yaml`：

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

- [ ] **步骤 2：忽略本地目录配置**

在 `.gitignore` 增加：

```gitignore
config/models.yaml
```

保留 `config/models.example.yaml` 可提交。

- [ ] **步骤 3：更新本地 `.env`**

修改本地 `.env`，将任务 32 的单 provider 示例调整为目录入口：

```bash
DEEPSEEK_API_KEY=
QWEN_API_KEY=
ANANHU_MODEL_CATALOG=config/models.yaml
ANANHU_REAL_MODEL_SMOKE=0
ANANHU_REAL_MODEL=deepseek-chat
```

预期：`.env` 仍被 Git 忽略，且不包含真实密钥。

- [ ] **步骤 4：验证 Git 不会提交本地密钥文件**

运行：

```bash
git status --short
```

预期：显示 `.gitignore` 和 `config/models.example.yaml` 变更；不显示 `.env` 和 `config/models.yaml`。

- [ ] **步骤 5：Commit**

运行：

```bash
git add .gitignore config/models.example.yaml
git commit -m "chore(model): 增加模型目录示例配置"
```

预期：只提交示例配置和忽略规则。

## 任务 5：完整回归与差分验收

**文件：**
- 修改：`docs/superpowers/plans/2026-07-10-framework-neutral-langgraph-evolution.md`

- [ ] **步骤 1：运行模型相关测试**

运行：

```bash
uv run pytest tests/test_model_catalog_config.py tests/test_model_router_config.py tests/test_model_gateway_contract.py -v
```

预期：模型目录、router、gateway contract 测试 PASS；真实 smoke 在未设置 `ANANHU_REAL_MODEL_SMOKE=1` 时 SKIP。

- [ ] **步骤 2：运行全量测试**

运行：

```bash
uv run pytest -v
```

预期：所有测试 PASS；允许真实模型 smoke 保持 SKIP。

- [ ] **步骤 3：运行 CLI smoke**

运行：

```bash
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
```

预期：CLI 正常输出工伤待遇辅助测算相关回答，并记录模型 trace；默认 Fake 路径不访问网络。

- [ ] **步骤 4：运行双运行时差分**

运行：

```bash
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```

预期：Native/LangGraph 差分结果保持等价，不因模型目录引入 runtime 差异。

- [ ] **步骤 5：更新任务计划状态**

在 `docs/superpowers/plans/2026-07-10-framework-neutral-langgraph-evolution.md` 中为任务 33 增加完成记录：

```markdown
### 任务 33：Provider/Profile 模型目录

状态：已完成

验证：

- `uv run pytest tests/test_model_catalog_config.py tests/test_model_router_config.py tests/test_model_gateway_contract.py -v`
- `uv run pytest -v`
- `uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"`
- `uv run ananhu-agent eval data/eval/eval_cases.jsonl`
```

- [ ] **步骤 6：Commit**

运行：

```bash
git add docs/superpowers/plans/2026-07-10-framework-neutral-langgraph-evolution.md
git commit -m "docs(plan): 标记模型目录任务完成"
```

预期：生成验收记录提交。

## 最终交付检查

- [ ] 运行 `git status --short --branch`，确认只剩 `.env` 这类被忽略本地文件不进入提交。
- [ ] 运行 `git log --oneline -8 --decorate`，确认任务分支包含文档、配置、router 和验收提交。
- [ ] 向用户汇报改动范围、验证结果和待合并分支，等待用户明确确认后才合并回 `mvp`。
