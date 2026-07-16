"""Kernel 跨模块共享的严格 Schema 与 JSON 数据边界。"""

from __future__ import annotations

from typing import TypeAlias, TypeVar, cast

from pydantic import BaseModel, ConfigDict, model_validator
from typing_extensions import TypeAliasType

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue = TypeAliasType(
    "JsonValue",
    JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"],
)
JsonObject = TypeAliasType("JsonObject", dict[str, JsonValue])

T = TypeVar("T")


class _FrozenJsonDict(dict[str, JsonValue]):
    """保持 JSON dict wire shape，同时拒绝运行期原地修改。"""

    @staticmethod
    def _immutable(*args: object, **kwargs: object) -> None:
        raise TypeError("frozen JSON value cannot be modified")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


class _FrozenJsonList(list[JsonValue]):
    """保持 JSON list wire shape，同时拒绝运行期原地修改。"""

    @staticmethod
    def _immutable(*args: object, **kwargs: object) -> None:
        raise TypeError("frozen JSON value cannot be modified")

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable


def _freeze_nested(value: T) -> T:
    if isinstance(value, (_FrozenJsonDict, _FrozenJsonList)):
        return value
    if isinstance(value, dict):
        return cast(
            T,
            _FrozenJsonDict(
                {key: _freeze_nested(item) for key, item in value.items()}
            ),
        )
    if isinstance(value, list):
        return cast(T, _FrozenJsonList(_freeze_nested(item) for item in value))
    if isinstance(value, tuple):
        return cast(T, tuple(_freeze_nested(item) for item in value))
    return value


class KernelSchema(BaseModel):
    """公共 Schema 的严格、不可变和深层 JSON 冻结基类。"""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    @model_validator(mode="after")
    def freeze_json_values(self) -> KernelSchema:
        for field_name in type(self).model_fields:
            value = getattr(self, field_name)
            frozen = _freeze_nested(value)
            if frozen is not value:
                object.__setattr__(self, field_name, frozen)
        return self
