from __future__ import annotations

from pathlib import Path

from ananhu_agent.config.settings import RuntimeSettings


def test_runtime_settings_loads_model_catalog_from_dotenv(tmp_path, monkeypatch) -> None:
    """CLI 组合根创建设置时应自动读取项目当前目录的 .env。"""

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'ANANHU_MODEL_CATALOG="config/models.yaml"\n',
        encoding="utf-8",
    )

    settings = RuntimeSettings()

    assert settings.model_catalog == Path("config/models.yaml")


def test_exported_environment_overrides_dotenv_value(tmp_path, monkeypatch) -> None:
    """显式 shell 环境优先于 .env，便于部署环境覆盖本地默认值。"""

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'ANANHU_MODEL_CATALOG="config/models.yaml"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("ANANHU_MODEL_CATALOG", "config/override.yaml")

    settings = RuntimeSettings()

    assert settings.model_catalog == Path("config/override.yaml")
