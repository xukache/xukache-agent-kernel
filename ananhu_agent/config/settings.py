from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, PrivateAttr, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """MVP 运行时配置入口。

    默认模型走确定性 fake provider。真实 provider 的密钥独立于 profile 保存，避免被
    profile trace 或评测 artifact 意外序列化。
    """

    runtime_dir: Path = Path(".ananhu-runtime")
    runtime: Literal["native", "langgraph"] = "langgraph"
    prompt_template_dir: Path = Path("ananhu_agent/prompts/templates")
    # 配置目录优先；以下三个字段保留为 v0.5 单 provider 兼容入口。
    model_catalog: Path | None = None
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
    # 仅 CLI 组合根注入的 dotenv 值；使用私有属性，避免密钥进入 settings 序列化结果。
    _dotenv_values: dict[str, str] = PrivateAttr(default_factory=dict)

    model_config = SettingsConfigDict(env_prefix="ANANHU_", extra="ignore")

    def set_dotenv_values(self, values: dict[str, str]) -> None:
        """保存 CLI 本地 dotenv 值，不修改进程级环境变量。"""

        self._dotenv_values = values

    def model_environment_value(self, name: str) -> str | None:
        """shell 环境优先，其次读取仅属于当前 CLI 配置的 dotenv 值。"""

        import os

        if name in os.environ:
            return os.environ[name]
        return self._dotenv_values.get(name)
