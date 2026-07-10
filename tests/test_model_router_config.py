import pytest

from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.infrastructure.models.fake import FakeModelGateway
from ananhu_agent.infrastructure.models.openai_compatible import OpenAICompatibleModelGateway
from ananhu_agent.models.model_router import ModelRouter
from ananhu_agent.ports.model_gateway import ModelErrorCode, ModelGatewayError


def test_model_router_returns_configured_profile():
    settings = RuntimeSettings(
        models={
            "intent_fast": {
                "provider": "fake",
                "model": "deterministic-intent",
                "temperature": 0,
            }
        }
    )

    profile = ModelRouter(settings).get_profile("intent_fast")

    assert profile["provider"] == "fake"
    assert profile["model"] == "deterministic-intent"


def test_model_router_builds_gateway_from_provider_neutral_profile():
    assert isinstance(ModelRouter(RuntimeSettings()).gateway_for("intent_fast"), FakeModelGateway)

    router = ModelRouter(RuntimeSettings(
        model_api_key="contract-secret",
        model_base_url="https://model.example.test/v1",
        models={
            "intent_fast": {
                "provider": "openai_compatible",
                "model": "provider-model",
                "temperature": 0,
                "timeout_seconds": 12,
            }
        },
    ))

    assert isinstance(router.gateway_for("intent_fast"), OpenAICompatibleModelGateway)


def test_model_router_rejects_real_provider_without_secret():
    router = ModelRouter(RuntimeSettings(
        model_base_url="https://model.example.test/v1",
        models={
            "intent_fast": {
                "provider": "openai_compatible",
                "model": "provider-model",
            }
        },
    ))

    with pytest.raises(ModelGatewayError) as captured:
        router.gateway_for("intent_fast")

    assert captured.value.code is ModelErrorCode.CONFIGURATION
