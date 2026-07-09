from __future__ import annotations

from ananhu_agent.models.fake_model import FakeModelClient


class ModelRouter:
    """按模型 profile 返回客户端的最小路由器。

    后续接入真实 Agno / LLM 客户端时，调用方仍只依赖 `client_for` 协议。
    """

    def __init__(self) -> None:
        self.fake_client = FakeModelClient()

    def client_for(self, model_profile: str) -> FakeModelClient:
        return self.fake_client
