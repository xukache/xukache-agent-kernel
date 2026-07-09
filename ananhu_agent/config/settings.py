from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """MVP 运行时配置入口。

    当前模型仍默认走确定性 fake provider，但 profile/provider/model 参数必须集中配置，
    以便后续接入 OpenAI-compatible、DashScope、DeepSeek 等真实模型时不改 Agent 协议。
    """

    runtime_dir: Path = Path(".ananhu-runtime")
    prompt_template_dir: Path = Path("ananhu_agent/prompts/templates")
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
