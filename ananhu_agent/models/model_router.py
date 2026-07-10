from __future__ import annotations

from typing import Any

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
        self._gateways: dict[str, ModelGateway] = {}

    def get_profile(self, profile_name: str) -> dict[str, Any]:
        """返回模型 profile 配置，供 trace 和运行报告记录。"""

        return dict(self.settings.models[profile_name])

    def gateway_for(self, model_profile: str) -> ModelGateway:
        if model_profile in self._gateways:
            return self._gateways[model_profile]

        profile = self.get_profile(model_profile)
        provider = profile["provider"]
        if provider == "fake":
            gateway: ModelGateway = FakeModelGateway()
        elif provider == "openai_compatible":
            api_key = self.settings.model_api_key
            if api_key is None or not self.settings.model_base_url:
                raise ModelGatewayError(
                    ModelErrorCode.CONFIGURATION,
                    "OpenAI-compatible provider 缺少 API key 或 base URL",
                    provider=provider,
                    retryable=False,
                )
            gateway = OpenAICompatibleModelGateway(
                api_key=api_key.get_secret_value(),
                base_url=self.settings.model_base_url,
                model=profile["model"],
                temperature=float(profile.get("temperature", 0)),
                timeout_seconds=float(profile.get("timeout_seconds", 30)),
                input_cost_per_million=profile.get("input_cost_per_million"),
                output_cost_per_million=profile.get("output_cost_per_million"),
                currency=profile.get("currency", "USD"),
            )
        else:
            raise ModelGatewayError(
                ModelErrorCode.CONFIGURATION,
                f"不支持的模型 provider: {provider}",
                provider=str(provider),
                retryable=False,
            )
        self._gateways[model_profile] = gateway
        return gateway
