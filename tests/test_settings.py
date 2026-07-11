from __future__ import annotations

import os
from pathlib import Path

import pytest

from ananhu_agent.cli.main import _cli_settings
from ananhu_agent.config.model_catalog import load_model_catalog
from ananhu_agent.config.settings import RuntimeSettings


def test_runtime_settings_does_not_read_dotenv_by_default(tmp_path, monkeypatch) -> None:
    """离线 Runtime 与 contract test 不受开发机 .env 配置影响。"""

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'ANANHU_MODEL_CATALOG="config/models.yaml"\n',
        encoding="utf-8",
    )

    settings = RuntimeSettings()

    assert settings.model_catalog is None


def test_cli_settings_loads_dotenv_and_exported_environment_overrides_it(tmp_path, monkeypatch) -> None:
    """CLI 入口读取 .env，但部署环境变量仍拥有更高优先级。"""

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'ANANHU_MODEL_CATALOG="config/models.yaml"\n',
        encoding="utf-8",
    )

    assert _cli_settings(tmp_path).model_catalog == Path("config/models.yaml")

    monkeypatch.setenv("ANANHU_MODEL_CATALOG", "config/override.yaml")

    settings = _cli_settings(tmp_path)

    assert settings.model_catalog == Path("config/override.yaml")


def test_cli_dotenv_exports_provider_key_for_yaml_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """模型目录通过环境变量名引用的密钥也必须在 CLI 入口可见。"""

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
    (tmp_path / ".env").write_text(
        'ANANHU_MODEL_CATALOG="models.yaml"\nDEEPSEEK_API_KEY="dotenv-model-key"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANANHU_MODEL_CATALOG", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    settings = _cli_settings(tmp_path)
    catalog = load_model_catalog(settings)

    provider = catalog.provider_for_profile("intent_fast")
    assert provider.api_key is not None
    assert provider.api_key.get_secret_value() == "dotenv-model-key"
    assert os.getenv("DEEPSEEK_API_KEY") is None
    assert RuntimeSettings().model_catalog is None

    copied_catalog = load_model_catalog(
        settings.model_copy(update={"runtime_dir": tmp_path / "runtime-copy"})
    )
    copied_provider = copied_catalog.provider_for_profile("intent_fast")
    assert copied_provider.api_key is not None
    assert copied_provider.api_key.get_secret_value() == "dotenv-model-key"


def test_cli_dotenv_does_not_override_exported_provider_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """部署环境中的 provider 密钥优先于本机 dotenv。"""

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
    (tmp_path / ".env").write_text(
        'ANANHU_MODEL_CATALOG="models.yaml"\nDEEPSEEK_API_KEY="dotenv-model-key"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANANHU_MODEL_CATALOG", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "exported-model-key")

    catalog = load_model_catalog(_cli_settings(tmp_path))

    provider = catalog.provider_for_profile("intent_fast")
    assert provider.api_key is not None
    assert provider.api_key.get_secret_value() == "exported-model-key"
