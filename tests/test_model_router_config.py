from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.models.model_router import ModelRouter


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
