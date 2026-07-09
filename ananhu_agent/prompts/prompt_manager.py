from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RenderedPrompt:
    metadata: dict[str, Any]
    text: str


class PromptManager:
    """从版本化 YAML 模板渲染完整 prompt，避免 Agent 直接拼接。"""

    def __init__(self, template_dir: Path) -> None:
        self.template_dir = template_dir

    def render(self, prompt_id: str, sections: dict[str, str]) -> RenderedPrompt:
        path = self.template_dir / f"{prompt_id}.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        body = raw["template"]

        for key, value in sections.items():
            body = body.replace("{{ " + key + " }}", value)

        return RenderedPrompt(metadata=raw["metadata"], text=body)
