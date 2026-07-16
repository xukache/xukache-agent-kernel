"""Agent 的长期只读装配定义。"""

from __future__ import annotations

from dataclasses import dataclass

from agent_kernel.model import Model


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
    eq=False,
)
class AgentDefinition:
    """组合长期 Instructions、Model 和执行上限，不保存单次调用数据。"""

    definition_id: str
    revision: str
    instructions: str
    model: Model
    max_model_rounds: int

    def __post_init__(self) -> None:
        for field_name in ("definition_id", "revision", "instructions"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-blank string")

        if not isinstance(self.model, Model):
            raise ValueError("model must satisfy the Model Protocol")

        if (
            isinstance(self.max_model_rounds, bool)
            or not isinstance(self.max_model_rounds, int)
            or self.max_model_rounds < 1
        ):
            raise ValueError("max_model_rounds must be a positive integer")
