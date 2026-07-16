# C1 Agent 公共调用边界实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用
> `superpowers:test-driven-development` 按步骤实现。项目规则优先于通用的频繁
> commit 建议：C1 实现结果获得用户确认前不得提交、勾选或合并。

**目标：** 实现已确认的 `AgentDefinition`、`AgentInput`、`AgentResult`、共享
`KernelSchema` / `ErrorInfo` 和稳定公开导入路径，为 C2-C4 提供不包含执行行为的
Agent 公共调用边界。

**架构：** 共享 JSON、Schema 和错误证据放入 `agent_kernel.contracts`；Model
迁移到共享 Schema 后保持现有公开行为；Agent 专属 Definition、Input、Result、
状态和错误码放入 `agent_kernel.agent`。C1 不创建 Agent Engine，不调用 Model，
不引入 Tool、Memory、Runtime 或 Provider 实现。

**技术栈：** Python 3.11、Pydantic 2.13.4、typing.Protocol、frozen dataclass、
pytest 8.4.2、uv。

**设计事实源：**

- `DEV_SPEC.md` 第 5.3.2 节、C1 任务和任务状态。
- `docs/superpowers/specs/2026-07-16-agent-kernel-agent-contract-c1.md`。
- `docs/backend-conventions.md`。

---

## 文件结构

### 创建

| 文件 | 职责 |
|---|---|
| `src/agent_kernel/contracts/schemas.py` | `KernelSchema`、共享 JSON 类型和深层冻结实现 |
| `src/agent_kernel/agent/__init__.py` | Agent 稳定公开入口 |
| `src/agent_kernel/agent/definition.py` | `AgentDefinition` 及本地装配校验 |
| `src/agent_kernel/agent/errors.py` | `AgentErrorCode` |
| `src/agent_kernel/agent/schemas.py` | `AgentInput`、`AgentResult`、状态和停止原因 |
| `tests/unit/contracts/test_error_info.py` | `ErrorInfo` 合同 |
| `tests/unit/agent/test_agent_definition.py` | Definition 合同 |
| `tests/unit/agent/test_agent_schemas.py` | Input / Result 合同 |

### 修改

| 文件 | 职责 |
|---|---|
| `src/agent_kernel/contracts/errors.py` | 增加 `ErrorSource` 和 `ErrorInfo` |
| `src/agent_kernel/contracts/__init__.py` | 导出共享 Schema 和错误契约 |
| `src/agent_kernel/model/schemas.py` | 改用共享 `KernelSchema` 和 JSON 类型 |
| `src/agent_kernel/model/errors.py` | 从 contracts 导入 `JsonObject` |
| `src/adapters/model/volcengine.py` | 从 contracts 导入共享 JSON 类型 |
| `tests/unit/model/test_model_schemas.py` | 固定共享 JSON 深层不可变回归 |

### 不创建或修改

- 不创建 `src/agent_kernel/agent/engine.py`。
- 不修改 `src/agent_kernel/__init__.py` 的空顶层导出。
- 不新增 Agent Contract Test、Integration Test 或 RD-002。
- 不修改 C2-C5、D-G 的任务状态。
- C1 实现验证通过后仍保持 `[~]`，等待用户确认结果。

---

### 任务 1：建立共享 KernelSchema 和不可变 JSON 边界

**文件：**

- 创建：`src/agent_kernel/contracts/schemas.py`
- 修改：`src/agent_kernel/contracts/__init__.py`
- 修改：`src/agent_kernel/model/schemas.py`
- 修改：`src/agent_kernel/model/errors.py`
- 修改：`src/adapters/model/volcengine.py`
- 测试：`tests/unit/model/test_model_schemas.py`

- [ ] **步骤 1：先增加会失败的深层不可变回归测试**

在 `tests/unit/model/test_model_schemas.py` 追加：

```python
def test_model_request_json_values_are_detached_and_deeply_immutable() -> None:
    source = {
        "schema": {
            "type": "object",
            "required": ["result"],
        }
    }
    request = ModelRequest(
        input={"task": "calculate"},
        output_schema=source["schema"],
        runtime_metadata={"labels": ["rd-001"]},
    )

    source["schema"]["required"].append("unexpected")

    assert request.output_schema == {
        "type": "object",
        "required": ["result"],
    }

    with pytest.raises(TypeError, match="frozen JSON"):
        request.output_schema["required"].append("mutated")  # type: ignore[index,union-attr]

    with pytest.raises(TypeError, match="frozen JSON"):
        request.runtime_metadata["labels"] = ["changed"]
```

- [ ] **步骤 2：运行测试，确认现有浅冻结行为失败**

运行：

```bash
uv run pytest -q \
  tests/unit/model/test_model_schemas.py::test_model_request_json_values_are_detached_and_deeply_immutable
```

预期：FAIL，至少一个 `pytest.raises(TypeError)` 没有捕获到异常，证明嵌套
dict / list 当前仍可原地修改。

- [ ] **步骤 3：创建共享 Schema 和 JSON 类型**

创建 `src/agent_kernel/contracts/schemas.py`：

```python
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
```

实现约束：

- `_FrozenJsonDict` 必须继承 `dict`，`_FrozenJsonList` 必须继承 `list`，保证
  `jsonschema`、Pydantic JSON 序列化和 Provider payload 仍识别标准 wire shape。
- 不导出两个内部冻结容器；公共调用者只依赖 `JsonValue`、`JsonObject` 和
  `KernelSchema`。
- `model_dump()` 和 `model_dump_json()` 必须输出普通 JSON 结构。

- [ ] **步骤 4：迁移 Model 到共享 Schema**

在 `src/agent_kernel/model/schemas.py`：

```python
from enum import Enum

from pydantic import Field, model_validator

from agent_kernel.contracts.schemas import (
    JsonObject,
    JsonPrimitive,
    JsonValue,
    KernelSchema,
)


class ModelSchema(KernelSchema):
    """Model 数据跨越 Core 与 Adapter 时使用的严格不可变基类。"""
```

删除该文件内重复的 `JsonPrimitive`、`JsonValue`、`JsonObject` 和
`ModelSchema.model_config` 定义。将可变默认值改为工厂：

```python
class ModelRequest(ModelSchema):
    runtime_metadata: JsonObject = Field(default_factory=dict)


class ModelResponse(ModelSchema):
    provider_metadata: JsonObject = Field(default_factory=dict)
```

保留其他字段和 validator 不变。

在 `src/agent_kernel/model/errors.py` 改为：

```python
from agent_kernel.contracts import JsonObject, KernelError
```

在 `src/adapters/model/volcengine.py` 改为：

```python
from agent_kernel.contracts import JsonObject, JsonValue
```

删除对应的 `agent_kernel.model.schemas` 私有 JSON 类型导入。

在 `src/agent_kernel/contracts/__init__.py` 导出：

```python
from .errors import KernelError
from .schemas import JsonObject, JsonPrimitive, JsonValue, KernelSchema

__all__ = [
    "JsonObject",
    "JsonPrimitive",
    "JsonValue",
    "KernelError",
    "KernelSchema",
]
```

- [ ] **步骤 5：运行 Model 与 Adapter 回归**

运行：

```bash
uv run pytest -q tests/unit/model/test_model_schemas.py
uv run pytest -q tests/contract/model/test_model_contract.py
uv run pytest -q tests/integration/model/test_volcengine_adapter.py
```

预期：全部 PASS。特别确认：

- 冻结后的 JSON Schema 仍能通过 `jsonschema` 校验。
- Volcengine 请求体仍能被 `httpx` 序列化。
- `ModelRequest` / `ModelResponse` JSON 输出没有改变。

- [ ] **步骤 6：检查本任务 diff**

运行：

```bash
git diff --check
git diff -- src/agent_kernel/contracts src/agent_kernel/model \
  src/adapters/model/volcengine.py tests/unit/model/test_model_schemas.py
```

预期：只有共享 Schema、Model 迁移和对应测试；不出现 Agent Engine 或任务状态
变更。

---

### 任务 2：实现共享 ErrorInfo

**文件：**

- 修改：`src/agent_kernel/contracts/errors.py`
- 修改：`src/agent_kernel/contracts/__init__.py`
- 创建：`tests/unit/contracts/test_error_info.py`

- [ ] **步骤 1：先编写 ErrorInfo 失败测试**

创建 `tests/unit/contracts/test_error_info.py`：

```python
"""共享 ErrorInfo 的确定性合同测试。"""

import json

import pytest
from pydantic import ValidationError

from agent_kernel.contracts import ErrorInfo, ErrorSource


def test_error_info_is_strict_immutable_and_json_serializable() -> None:
    source_details = {"provider": {"request_ids": ["request-1"]}}
    error = ErrorInfo(
        code="model.timeout",
        message="model request timed out",
        source=ErrorSource.MODEL,
        retryable=True,
        details=source_details,
    )

    source_details["provider"]["request_ids"].append("request-2")

    assert error.details == {"provider": {"request_ids": ["request-1"]}}
    assert json.loads(error.model_dump_json())["code"] == "model.timeout"

    with pytest.raises(TypeError, match="frozen JSON"):
        error.details["provider"]["request_ids"].append("mutated")  # type: ignore[index]

    with pytest.raises(ValidationError):
        ErrorInfo(
            code="model.timeout",
            message="timeout",
            source=ErrorSource.MODEL,
            retryable=1,
        )


@pytest.mark.parametrize("code", ["", "timeout", "Model.Timeout", "model timeout"])
def test_error_info_rejects_invalid_error_codes(code: str) -> None:
    with pytest.raises(ValidationError):
        ErrorInfo(
            code=code,
            message="invalid",
            source=ErrorSource.MODEL,
            retryable=False,
        )


def test_error_info_rejects_blank_message_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ErrorInfo(
            code="agent.internal",
            message="   ",
            source=ErrorSource.AGENT,
            retryable=False,
        )

    with pytest.raises(ValidationError):
        ErrorInfo(
            code="agent.internal",
            message="internal failure",
            source=ErrorSource.AGENT,
            retryable=False,
            traceback="secret",
        )
```

- [ ] **步骤 2：运行测试，确认公共类型尚不存在**

运行：

```bash
uv run pytest -q tests/unit/contracts/test_error_info.py
```

预期：测试收集阶段 FAIL，无法从 `agent_kernel.contracts` 导入 `ErrorInfo` 或
`ErrorSource`。

- [ ] **步骤 3：实现 ErrorSource 和 ErrorInfo**

将 `src/agent_kernel/contracts/errors.py` 扩展为：

```python
"""Kernel 运行时错误与公开失败证据。"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from .schemas import JsonObject, KernelSchema


class KernelError(Exception):
    """合法运行中的 Kernel 失败传播基类。"""


class ErrorSource(str, Enum):
    """当前已确认的错误所有者。"""

    AGENT = "agent"
    MODEL = "model"


class ErrorInfo(KernelSchema):
    """Result 和 Event 使用的脱敏、可序列化失败证据。"""

    code: str = Field(
        min_length=3,
        pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$",
    )
    message: str = Field(min_length=1)
    source: ErrorSource
    retryable: bool
    details: JsonObject = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("error message must not be blank")
        return value
```

在 `src/agent_kernel/contracts/__init__.py` 增加：

```python
from .errors import ErrorInfo, ErrorSource, KernelError
```

并把 `"ErrorInfo"`、`"ErrorSource"` 加入 `__all__`。

- [ ] **步骤 4：运行 ErrorInfo 和 Model 错误回归**

运行：

```bash
uv run pytest -q tests/unit/contracts/test_error_info.py
uv run pytest -q tests/contract/model/test_model_contract.py
```

预期：全部 PASS，现有 `ModelError` 仍继承 `KernelError`。

- [ ] **步骤 5：检查本任务 diff**

运行：

```bash
git diff --check
git diff -- src/agent_kernel/contracts tests/unit/contracts
```

预期：ErrorInfo 不包含 Exception、traceback、Provider SDK 对象或凭证字段。

---

### 任务 3：实现 AgentDefinition 和 AgentErrorCode

**文件：**

- 创建：`src/agent_kernel/agent/definition.py`
- 创建：`src/agent_kernel/agent/errors.py`
- 创建：`src/agent_kernel/agent/__init__.py`
- 创建：`tests/unit/agent/test_agent_definition.py`

- [ ] **步骤 1：先编写 AgentDefinition 失败测试**

创建 `tests/unit/agent/test_agent_definition.py`：

```python
"""AgentDefinition 的只读装配合同测试。"""

from collections.abc import AsyncIterator
from dataclasses import FrozenInstanceError

import pytest

from agent_kernel.agent import AgentDefinition
from agent_kernel.model import (
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
)


class StubModel:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("C1 must not call the model")

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        async def empty() -> AsyncIterator[ModelStreamChunk]:
            if False:
                yield ModelStreamChunk(text_delta="unreachable")

        return empty()


class InvalidModel:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError


def test_agent_definition_is_frozen_and_uses_identity_equality() -> None:
    model = StubModel()
    definition = AgentDefinition(
        definition_id="calculator",
        revision="1",
        instructions="Return a structured calculation result.",
        model=model,
        max_model_rounds=2,
    )
    same_fields = AgentDefinition(
        definition_id="calculator",
        revision="1",
        instructions="Return a structured calculation result.",
        model=model,
        max_model_rounds=2,
    )

    assert definition.model is model
    assert definition != same_fields

    with pytest.raises(FrozenInstanceError):
        definition.instructions = "changed"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("definition_id", ""),
        ("definition_id", "   "),
        ("revision", ""),
        ("instructions", "   "),
    ],
)
def test_agent_definition_rejects_blank_text_fields(
    field_name: str,
    value: str,
) -> None:
    values = {
        "definition_id": "calculator",
        "revision": "1",
        "instructions": "Calculate.",
    }
    values[field_name] = value

    with pytest.raises(ValueError):
        AgentDefinition(
            **values,
            model=StubModel(),
            max_model_rounds=1,
        )


@pytest.mark.parametrize("max_model_rounds", [0, -1, True, 1.5])
def test_agent_definition_rejects_invalid_model_round_limits(
    max_model_rounds: object,
) -> None:
    with pytest.raises(ValueError):
        AgentDefinition(
            definition_id="calculator",
            revision="1",
            instructions="Calculate.",
            model=StubModel(),
            max_model_rounds=max_model_rounds,
        )


def test_agent_definition_rejects_objects_outside_model_protocol() -> None:
    with pytest.raises(ValueError, match="Model Protocol"):
        AgentDefinition(
            definition_id="calculator",
            revision="1",
            instructions="Calculate.",
            model=InvalidModel(),
            max_model_rounds=1,
        )
```

- [ ] **步骤 2：运行测试，确认 Agent 包尚不存在**

运行：

```bash
uv run pytest -q tests/unit/agent/test_agent_definition.py
```

预期：测试收集阶段 FAIL，无法导入 `agent_kernel.agent`。

- [ ] **步骤 3：实现 AgentErrorCode**

创建 `src/agent_kernel/agent/errors.py`：

```python
"""Agent 边界拥有的稳定错误码。"""

from enum import Enum


class AgentErrorCode(str, Enum):
    LIMIT = "agent.limit"
    CANCELLED = "agent.cancelled"
    INTERNAL = "agent.internal"
```

- [ ] **步骤 4：实现 AgentDefinition**

创建 `src/agent_kernel/agent/definition.py`：

```python
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
```

创建最小 `src/agent_kernel/agent/__init__.py`：

```python
"""Agent Core 的公共调用契约。"""

from .definition import AgentDefinition
from .errors import AgentErrorCode

__all__ = [
    "AgentDefinition",
    "AgentErrorCode",
]
```

- [ ] **步骤 5：运行 Definition 和架构测试**

运行：

```bash
uv run pytest -q tests/unit/agent/test_agent_definition.py
uv run pytest -q tests/architecture
```

预期：全部 PASS。测试期间 `StubModel.generate` / `stream` 不被调用。

- [ ] **步骤 6：检查本任务 diff**

运行：

```bash
git diff --check
git diff -- src/agent_kernel/agent tests/unit/agent/test_agent_definition.py
```

预期：AgentDefinition 不包含 input、output_schema、Tool、Memory、run_id 或
Provider 配置。

---

### 任务 4：实现 AgentInput

**文件：**

- 创建：`src/agent_kernel/agent/schemas.py`
- 修改：`src/agent_kernel/agent/__init__.py`
- 创建：`tests/unit/agent/test_agent_schemas.py`

- [ ] **步骤 1：先编写 AgentInput 失败测试**

创建 `tests/unit/agent/test_agent_schemas.py`，先加入：

```python
"""AgentInput 和 AgentResult 的确定性合同测试。"""

import json

import pytest
from pydantic import ValidationError

from agent_kernel.agent import AgentInput


def test_agent_input_is_strict_serializable_and_deeply_immutable() -> None:
    source = {
        "input": {"numbers": [9, 6]},
        "output_schema": {
            "type": "object",
            "required": ["result"],
        },
        "application_metadata": {
            "source": "learning",
            "labels": ["rd-002"],
        },
    }
    agent_input = AgentInput(**source)

    source["input"]["numbers"].append(100)
    source["application_metadata"]["labels"].append("changed")

    assert agent_input.input == {"numbers": [9, 6]}
    assert agent_input.application_metadata == {
        "source": "learning",
        "labels": ["rd-002"],
    }
    assert json.loads(agent_input.model_dump_json())["output_schema"]["required"] == [
        "result"
    ]

    with pytest.raises(TypeError, match="frozen JSON"):
        agent_input.input["numbers"].append(1)  # type: ignore[index,union-attr]


@pytest.mark.parametrize("input_value", ["", "   ", 42])
def test_agent_input_rejects_blank_text_and_invalid_types(
    input_value: object,
) -> None:
    with pytest.raises(ValidationError):
        AgentInput(input=input_value)


def test_agent_input_allows_empty_structured_input_and_rejects_extra_fields() -> None:
    assert AgentInput(input={}).input == {}

    with pytest.raises(ValidationError):
        AgentInput(input="calculate", model="provider-model")
```

- [ ] **步骤 2：运行测试，确认 AgentInput 尚不存在**

运行：

```bash
uv run pytest -q tests/unit/agent/test_agent_schemas.py
```

预期：测试收集阶段 FAIL，无法导入 `AgentInput`。

- [ ] **步骤 3：实现 AgentInput**

创建 `src/agent_kernel/agent/schemas.py`：

```python
"""Agent 单次调用输入和最终结果 Schema。"""

from __future__ import annotations

from pydantic import Field, field_validator

from agent_kernel.contracts import JsonObject, KernelSchema


class AgentInput(KernelSchema):
    """本次 Agent 调用数据，不重复携带 Definition 装配。"""

    input: str | JsonObject
    output_schema: JsonObject | None = None
    application_metadata: JsonObject = Field(default_factory=dict)

    @field_validator("input")
    @classmethod
    def reject_blank_text_input(
        cls,
        value: str | JsonObject,
    ) -> str | JsonObject:
        if isinstance(value, str) and not value.strip():
            raise ValueError("agent input text must not be blank")
        return value
```

在 `src/agent_kernel/agent/__init__.py` 增加：

```python
from .schemas import AgentInput
```

并把 `"AgentInput"` 加入 `__all__`。

- [ ] **步骤 4：运行 AgentInput 测试**

运行：

```bash
uv run pytest -q tests/unit/agent/test_agent_schemas.py
uv run pytest -q tests/unit/model/test_model_schemas.py
```

预期：全部 PASS。`application_metadata` 保持独立字段，不自动映射到
`ModelRequest.runtime_metadata`。

- [ ] **步骤 5：检查本任务 diff**

运行：

```bash
git diff --check
git diff -- src/agent_kernel/agent/schemas.py \
  src/agent_kernel/agent/__init__.py tests/unit/agent/test_agent_schemas.py
```

预期：AgentInput 不包含 model、instructions、max_model_rounds、run_id、deadline
或 cancellation。

---

### 任务 5：实现 AgentResult 状态与错误不变量

**文件：**

- 修改：`src/agent_kernel/agent/schemas.py`
- 修改：`src/agent_kernel/agent/__init__.py`
- 修改：`tests/unit/agent/test_agent_schemas.py`

- [ ] **步骤 1：追加 AgentResult 失败测试**

在 `tests/unit/agent/test_agent_schemas.py` 的 import 中加入：

```python
from agent_kernel.agent import (
    AgentResult,
    AgentStatus,
    AgentStopReason,
)
from agent_kernel.contracts import ErrorInfo, ErrorSource
from agent_kernel.model import ToolCall, Usage
```

追加：

```python
def test_agent_result_supports_success_failure_and_cancellation() -> None:
    succeeded = AgentResult(
        status=AgentStatus.SUCCEEDED,
        output={"result": 15},
        usage=Usage(input_tokens=10, output_tokens=3, total_tokens=13),
        model_id="real-model",
        stop_reason=AgentStopReason.COMPLETED,
    )
    failed = AgentResult(
        status=AgentStatus.FAILED,
        usage=Usage(),
        stop_reason=AgentStopReason.MAX_MODEL_ROUNDS,
        error=ErrorInfo(
            code="agent.limit",
            message="maximum model rounds reached",
            source=ErrorSource.AGENT,
            retryable=False,
        ),
        tool_calls=(
            ToolCall(
                call_id="call-1",
                name="add",
                arguments={"a": 9, "b": 6},
            ),
        ),
    )
    cancelled = AgentResult(
        status=AgentStatus.CANCELLED,
        usage=Usage(),
        stop_reason=AgentStopReason.CANCELLED,
        error=ErrorInfo(
            code="model.cancelled",
            message="model invocation cancelled",
            source=ErrorSource.MODEL,
            retryable=False,
        ),
    )

    assert succeeded.output == {"result": 15}
    assert succeeded.model_id == "real-model"
    assert failed.error is not None
    assert failed.error.code == "agent.limit"
    assert failed.tool_calls[0].name == "add"
    assert cancelled.status is AgentStatus.CANCELLED


@pytest.mark.parametrize(
    "result_data",
    [
        {
            "status": AgentStatus.SUCCEEDED,
            "output": None,
            "usage": Usage(),
            "model_id": "model",
            "stop_reason": AgentStopReason.COMPLETED,
        },
        {
            "status": AgentStatus.SUCCEEDED,
            "output": "done",
            "usage": Usage(),
            "model_id": None,
            "stop_reason": AgentStopReason.COMPLETED,
        },
        {
            "status": AgentStatus.FAILED,
            "output": "partial",
            "usage": Usage(),
            "stop_reason": AgentStopReason.ERROR,
            "error": ErrorInfo(
                code="model.format",
                message="invalid output",
                source=ErrorSource.MODEL,
                retryable=False,
            ),
        },
        {
            "status": AgentStatus.FAILED,
            "usage": Usage(),
            "stop_reason": AgentStopReason.ERROR,
            "error": None,
        },
        {
            "status": AgentStatus.CANCELLED,
            "usage": Usage(),
            "stop_reason": AgentStopReason.ERROR,
            "error": ErrorInfo(
                code="agent.cancelled",
                message="cancelled",
                source=ErrorSource.AGENT,
                retryable=False,
            ),
        },
    ],
)
def test_agent_result_rejects_invalid_status_combinations(
    result_data: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AgentResult(**result_data)
```

- [ ] **步骤 2：运行测试，确认 Result 类型尚不存在**

运行：

```bash
uv run pytest -q tests/unit/agent/test_agent_schemas.py
```

预期：测试收集或执行阶段 FAIL，无法导入或构造 `AgentResult`。

- [ ] **步骤 3：实现状态枚举和 AgentResult**

在 `src/agent_kernel/agent/schemas.py` 增加 imports：

```python
from enum import Enum

from pydantic import Field, field_validator, model_validator

from agent_kernel.contracts import ErrorInfo, JsonObject, KernelSchema
from agent_kernel.model import ToolCall, Usage
```

增加：

```python
class AgentStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStopReason(str, Enum):
    COMPLETED = "completed"
    MAX_MODEL_ROUNDS = "max_model_rounds"
    ERROR = "error"
    CANCELLED = "cancelled"


class AgentResult(KernelSchema):
    """一次 Agent 调用的最终结构化结果，不承担 Runtime Result 职责。"""

    status: AgentStatus
    output: str | JsonObject | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage
    model_id: str | None = None
    stop_reason: AgentStopReason
    error: ErrorInfo | None = None

    @field_validator("model_id")
    @classmethod
    def reject_blank_model_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("model_id must not be blank")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self) -> AgentResult:
        if self.status is AgentStatus.SUCCEEDED:
            if self.output is None:
                raise ValueError("succeeded result requires output")
            if self.model_id is None:
                raise ValueError("succeeded result requires model_id")
            if self.error is not None:
                raise ValueError("succeeded result cannot include error")
            if self.stop_reason is not AgentStopReason.COMPLETED:
                raise ValueError("succeeded result must stop as completed")
            return self

        if self.status is AgentStatus.FAILED:
            if self.output is not None:
                raise ValueError("failed result cannot include output")
            if self.error is None:
                raise ValueError("failed result requires error")
            if self.stop_reason not in {
                AgentStopReason.ERROR,
                AgentStopReason.MAX_MODEL_ROUNDS,
            }:
                raise ValueError("failed result has invalid stop_reason")
            return self

        if self.output is not None:
            raise ValueError("cancelled result cannot include output")
        if self.error is None:
            raise ValueError("cancelled result requires error")
        if self.stop_reason is not AgentStopReason.CANCELLED:
            raise ValueError("cancelled result must stop as cancelled")
        return self
```

在 `src/agent_kernel/agent/__init__.py` 导出：

```python
from .schemas import AgentInput, AgentResult, AgentStatus, AgentStopReason
```

并把 `"AgentResult"`、`"AgentStatus"`、`"AgentStopReason"` 加入 `__all__`。

- [ ] **步骤 4：运行完整 Agent Unit Tests**

运行：

```bash
uv run pytest -q tests/unit/agent
```

预期：全部 PASS，覆盖成功、失败、取消、limit 和非法状态组合。

- [ ] **步骤 5：验证 JSON 往返与公开导入**

在成功结果测试中补充：

```python
round_trip = AgentResult.model_validate_json(succeeded.model_dump_json())

assert round_trip == succeeded
```

运行：

```bash
uv run pytest -q tests/unit/agent/test_agent_schemas.py
uv run python -c \
  "from agent_kernel.agent import AgentDefinition, AgentInput, AgentResult"
```

预期：测试 PASS，公开导入命令退出码为 0。

- [ ] **步骤 6：检查本任务 diff**

运行：

```bash
git diff --check
git diff -- src/agent_kernel/agent tests/unit/agent
```

预期：不存在 Model 调用、Tool 执行、Memory scope、RunContext 或事件逻辑。

---

### 任务 6：累计验证、证据整理和用户确认门禁

**文件：**

- 检查：全部 C1 变更
- 不修改：`DEV_SPEC.md` 的 C1 完成状态

- [ ] **步骤 1：运行分层验证**

运行：

```bash
uv run pytest -q tests/unit/contracts
uv run pytest -q tests/unit/agent
uv run pytest -q tests/unit/model
uv run pytest -q tests/contract/model
uv run pytest -q tests/integration/model
uv run pytest -q tests/architecture
```

预期：全部 PASS。

- [ ] **步骤 2：运行全量测试与构建**

运行：

```bash
uv run pytest -q
uv lock --check
uv build
uv run python -c \
  "from agent_kernel.agent import AgentDefinition, AgentInput, AgentResult"
git diff --check
```

预期：

- 全量 pytest PASS。
- lock 文件无漂移。
- sdist 和 wheel 构建成功。
- 安装环境可以从 `agent_kernel.agent` 导入 C1 类型。
- diff 无空白错误。

- [ ] **步骤 3：检查范围和状态**

运行：

```bash
git status --short
git diff --stat
git diff --name-only
rg -n "\\| C1 \\|.*\\[~\\]" DEV_SPEC.md
test ! -e src/agent_kernel/agent/engine.py
```

预期：

- `.playwright-mcp/` 仍未纳入任务。
- 只出现本计划列出的源码、测试和已确认文档。
- C1 仍为 `[~]`。
- `agent/engine.py` 不存在。

- [ ] **步骤 4：向用户展示实现结果**

报告：

- 新增的公共类型和公开导入路径。
- 分层测试、全量测试和构建结果。
- 未运行 RD-002，因为它属于 C5。
- C1 未标记完成、未提交、未合并。

等待用户明确确认 C1 实现结果。

- [ ] **步骤 5：用户确认后提交 C1 实现**

只有用户确认后才运行：

```bash
git add \
  src/agent_kernel/contracts \
  src/agent_kernel/model \
  src/agent_kernel/agent \
  src/adapters/model/volcengine.py \
  tests/unit/contracts \
  tests/unit/model/test_model_schemas.py \
  tests/unit/agent
git diff --cached --check
git commit -m "feat(agent): add C1 public contracts"
```

提交后仍不自动勾选 C1 或合并回 `architecture`。完成状态、最终证据记录、提交和合并
应按用户下一步明确指令处理，避免把“代码已实现”和“任务已验收完成”混为一体。

---

## 计划自检

### 规格覆盖

| 已确认要求 | 对应任务 |
|---|---|
| 共享严格 Schema 与 JSON 防御性复制 | 任务 1 |
| ErrorInfo 和 Agent 错误码 | 任务 2、3 |
| AgentDefinition 字段与本地校验 | 任务 3 |
| AgentInput 与 application_metadata 边界 | 任务 4 |
| AgentResult 状态和 stop_reason 不变量 | 任务 5 |
| Model 回归、架构边界和构建 | 任务 1、6 |
| 不实现 C2-C5 行为 | 全部任务的范围检查 |
| 用户确认前不提交、勾选或合并 | 任务 6 |

### 类型一致性

- Definition 统一使用 `definition_id`，不引入 `agent_id`。
- 最大轮次统一使用 `max_model_rounds`。
- Input 与 ModelRequest 统一使用 `input` 和 `output_schema`。
- `application_metadata` 不映射为 `runtime_metadata`。
- Agent limit 同时表达为
  `stop_reason=max_model_rounds` 和 `error.code=agent.limit`。
- Model 错误保留 `model.*` code 和 `ErrorSource.MODEL`。

### 范围结论

该计划只覆盖 C1 公共数据和装配契约。C2 的 ModelRequest Builder、C3 的推理循环、
C4 的真实上限行为和 C5 的 RD-002 都不进入本计划。
