from __future__ import annotations

from typing import Any

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.models.fake_model import FakeModelClient


class ModelRouter:
    """按模型 profile 返回配置和客户端的最小路由器。

    后续接入真实 LLM 客户端时，调用方仍只依赖 `client_for` 协议。
    """

    def __init__(self, settings: RuntimeSettings | None = None) -> None:
        self.settings = settings or RuntimeSettings()
        self.fake_client = FakeModelClient()

    def get_profile(self, profile_name: str) -> dict[str, Any]:
        """返回模型 profile 配置，供 trace 和运行报告记录。"""

        return dict(self.settings.models[profile_name])

    def client_for(self, model_profile: str) -> FakeModelClient:
        profile = self.get_profile(model_profile)
        if profile["provider"] != "fake":
            raise ValueError(f"unsupported model provider: {profile['provider']}")
        return self.fake_client
