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

        return self.catalog.profile(profile_name).model_dump()

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
