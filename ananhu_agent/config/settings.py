from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """MVP 运行时配置入口。

    默认模型走确定性 fake provider。真实 provider 的密钥独立于 profile 保存，避免被
    profile trace 或评测 artifact 意外序列化。
    """

    runtime_dir: Path = Path(".ananhu-runtime")
    runtime: Literal["native", "langgraph"] = "langgraph"
    prompt_template_dir: Path = Path("ananhu_agent/prompts/templates")
    model_api_key: SecretStr | None = None
    model_base_url: str = ""
    models: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {
            "intent_fast": {
                "provider": "fake",
                "model": "deterministic-intent",
                "temperature": 0,
            }
        }
    )

    model_config = SettingsConfigDict(env_prefix="ANANHU_", extra="ignore")
