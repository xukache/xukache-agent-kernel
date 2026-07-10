from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.ports.model_gateway import ModelErrorCode, ModelGatewayError


_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ProviderConfig(BaseModel):
    """模型供应商配置，只保存密钥引用，不保存目录中的密钥明文。"""

    name: str
    protocol: Literal["fake", "openai_compatible"]
    base_url: str = ""
    api_key_env: str | None = None
    api_key: SecretStr | None = Field(default=None, exclude=True)

    @field_validator("api_key_env")
    @classmethod
    def _validate_api_key_env(cls, value: str | None) -> str | None:
        if value is not None and not _ENV_NAME_RE.fullmatch(value):
            raise ValueError("api_key_env must be an environment variable name")
        return value

    @model_validator(mode="after")
    def _validate_provider(self) -> ProviderConfig:
        if self.protocol == "openai_compatible" and not self.base_url.startswith("https://"):
            raise ValueError("openai_compatible provider base_url must use https")
        return self


class ModelProfileConfig(BaseModel):
    """业务可选择的模型档位；Agent 只引用 profile 名称。"""

    name: str
    provider: str
    model: str
    temperature: float = Field(default=0, ge=0, le=2)
    timeout_seconds: float = Field(default=30, gt=0)
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)
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
    """目录配置优先；未配置时把 v0.5 设置转换为同一目录协议。"""

    if settings.model_catalog is not None:
        return _load_yaml_catalog(settings.model_catalog)
    return _legacy_catalog(settings)


def _load_yaml_catalog(path: Path) -> ModelCatalog:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise _configuration_error(f"cannot read model catalog {path}: {exc}") from exc

    try:
        if not isinstance(raw, dict):
            raise TypeError("catalog root must be a mapping")
        providers_raw = raw.get("providers") or {}
        profiles_raw = raw.get("profiles") or {}
        if not isinstance(providers_raw, dict) or not isinstance(profiles_raw, dict):
            raise TypeError("providers and profiles must be mappings")

        providers = {
            name: _provider_from_yaml(name, value)
            for name, value in providers_raw.items()
        }
        profiles = {
            name: ModelProfileConfig(name=name, **(value or {}))
            for name, value in profiles_raw.items()
        }
        catalog = ModelCatalog(providers=providers, profiles=profiles)
        for profile_name in catalog.profiles:
            catalog.provider_for_profile(profile_name)
    except ModelGatewayError:
        raise
    except (TypeError, ValueError, ValidationError) as exc:
        raise _configuration_error(f"invalid model catalog: {exc}") from exc

    return catalog


def _provider_from_yaml(name: str, value: dict[str, Any] | None) -> ProviderConfig:
    provider = ProviderConfig(name=name, **(value or {}))
    if provider.api_key_env:
        secret = os.getenv(provider.api_key_env)
        if secret:
            provider = provider.model_copy(update={"api_key": SecretStr(secret)})
    return provider


def _legacy_catalog(settings: RuntimeSettings) -> ModelCatalog:
    providers = {"fake": ProviderConfig(name="fake", protocol="fake")}
    profiles: dict[str, ModelProfileConfig] = {}

    try:
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
        catalog = ModelCatalog(providers=providers, profiles=profiles)
        for profile_name in catalog.profiles:
            catalog.provider_for_profile(profile_name)
        return catalog
    except ModelGatewayError:
        raise
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise _configuration_error(f"invalid legacy model configuration: {exc}") from exc


def _configuration_error(message: str) -> ModelGatewayError:
    return ModelGatewayError(
        ModelErrorCode.CONFIGURATION,
        message,
        provider="model_catalog",
        retryable=False,
    )
