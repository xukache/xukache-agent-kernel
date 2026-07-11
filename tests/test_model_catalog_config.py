from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from ananhu_agent.config.model_catalog import load_model_catalog
from ananhu_agent.config.settings import RuntimeSettings
from ananhu_agent.ports.model_gateway import ModelErrorCode, ModelGatewayError


def test_loads_catalog_from_yaml_and_resolves_provider_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    assert provider.api_key is not None
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
        _env_file=None,
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
    provider = catalog.provider_for_profile("intent_fast")
    assert provider.api_key is not None
    assert provider.api_key.get_secret_value() == "legacy-secret"
