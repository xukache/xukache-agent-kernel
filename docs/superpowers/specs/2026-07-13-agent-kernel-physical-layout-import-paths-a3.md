# Agent Kernel A3 物理目录与公开导入路径设计

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | A3：确认物理目录与公开导入路径 |
| 日期 | 2026-07-13 |
| 状态 | 已完成 |
| 任务分支 | `task/a3-physical-layout-import-paths` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | A1、A2 已完成 |

本记录只定义物理组织和导入边界，不创建 Kernel 实现目录，不定义尚未由 B-G 任务确认的具体字段和方法签名。

## 2. A3 目标

A3 需要把已确认的逻辑边界转换为可实施的 Python 工程结构，同时保证：

- Kernel 不依赖 Application、Interface、Provider SDK 或具体存储。
- Adapter 只能依赖 Kernel 公共契约。
- Application / Composition Root 负责组装 Definition、Adapter 和配置。
- 测试可以分别证明确定性规则、公共契约、模块集成、架构边界和真实对话。
- 物理目录不会生成新的平行 Core，也不会恢复旧项目入口。

## 3. 目录方案

采用 `src/` layout，Kernel 的正式包名为 `agent_kernel`：

```text
project-root/
├── src/
│   ├── agent_kernel/
│   │   ├── __init__.py
│   │   ├── contracts/
│   │   │   ├── __init__.py
│   │   │   ├── protocols.py
│   │   │   ├── definitions.py
│   │   │   ├── schemas.py
│   │   │   ├── events.py
│   │   │   ├── errors.py
│   │   │   └── states.py
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── definition.py
│   │   │   └── engine.py
│   │   ├── workflow/
│   │   │   ├── __init__.py
│   │   │   ├── definition.py
│   │   │   └── engine.py
│   │   ├── tool/
│   │   │   ├── __init__.py
│   │   │   └── engine.py
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   └── service.py
│   │   ├── model/
│   │   │   ├── __init__.py
│   │   │   └── service.py
│   │   └── runtime/
│   │       ├── __init__.py
│   │       ├── context.py
│   │       ├── engine.py
│   │       └── execution.py
│   ├── adapters/
│   │   ├── model/
│   │   ├── memory/
│   │   ├── tool/
│   │   └── runtime/
│   ├── applications/
│   └── interfaces/
├── tests/
│   ├── unit/
│   │   ├── agent/
│   │   ├── workflow/
│   │   ├── tool/
│   │   ├── memory/
│   │   ├── model/
│   │   └── runtime/
│   ├── contract/
│   │   ├── model/
│   │   ├── memory/
│   │   ├── tool/
│   │   └── runtime/
│   ├── integration/
│   ├── architecture/
│   ├── real_dialogue/
│   └── support/
├── pyproject.toml
├── uv.lock
└── README.md
```

### 3.1 `agent_kernel/contracts`

这是 Kernel 的公共契约层，不是第七个 Core。它只保存跨模块共享的行为、装配、结构化数据、错误、事件和状态表达：

- `protocols.py`：Model、Tool、Memory、Runtime 等行为 Protocol。
- `definitions.py`：共享 DefinitionRef 和通用只读装配规则。
- `schemas.py`：KernelSchema 和跨模块 Schema 基础规则。
- `events.py`：公共事件信封和事件类型基础。
- `errors.py`：KernelError、ErrorInfo 和错误映射基础。
- `states.py`：共享状态引用和版本字段；不创建万能 KernelState。

模块专属 Definition、Input、Result 和 State 仍归属对应 Core，不集中到一个万能文件。

### 3.2 六个 Core

六个 Core 目录只承载各自语义和执行逻辑：

| 目录 | 负责 | 禁止依赖 |
|---|---|---|
| `agent/` | AgentDefinition、Agent 输入组装、推理循环和 Tool Call 决策 | Application、Interface、Provider SDK、具体 Backend |
| `workflow/` | WorkflowDefinition、步骤拓扑、状态推进和恢复位置 | Model Provider、业务数据库、Interface |
| `tool/` | Tool 定义、输入校验和一次调用结果 | 自然语言推理、Workflow 路由、共享业务状态 |
| `memory/` | Memory Protocol 对应的读取、写入和 scope 语义 | WorkflowState、业务事实和 UI 历史 |
| `model/` | Provider Neutral 的 Model 请求、响应和生成行为 | Prompt 所有权、Tool 执行、具体 Provider SDK |
| `runtime/` | RunContext、生命周期、取消、事件和 Execution 支撑 | 业务流程语义、Provider 私有状态 |

Execution 的 Hooks、Guardrails、Retry、Cancellation 和 Streaming 作为 `runtime/` 内的支撑能力，不单独创建顶层 Core。

### 3.3 Adapter、Application 与 Interface

- `adapters/`：具体 Provider、存储、Tool Backend 和 Runtime 实现。每个 Adapter 只能依赖 `agent_kernel.contracts` 或对应 Core Protocol。
- `applications/`：组合根和未来业务 Application。负责创建 Definition、选择 Adapter、注入配置和组织真实场景。
- `interfaces/`：未来 CLI、HTTP、MCP 或其他外部入口。第一阶段不创建外部 Interface 实现。

A3 只确定命名空间和依赖方向；具体 Provider 文件、业务应用和外部接口由后续任务按需创建。

## 4. 公开导入路径

### 4.1 稳定公开入口

对外只承诺以下导入层级：

```text
agent_kernel
agent_kernel.contracts
agent_kernel.agent
agent_kernel.workflow
agent_kernel.tool
agent_kernel.memory
agent_kernel.model
agent_kernel.runtime
```

`agent_kernel.__init__` 只重新导出已经确认的稳定公共类型和 Protocol；不重新导出 Adapter、Application、Interface 或内部执行对象。

### 4.2 非公开路径

以下路径不属于 Kernel 公共 API：

```text
adapters.*
applications.*
interfaces.*
agent_kernel.*.engine
agent_kernel.*.service
agent_kernel.runtime.execution
```

非公开路径可以在后续实现中调整，不作为外部调用者、测试 Fixture 或业务 Application 的稳定依赖。

### 4.3 导入规则

```text
interfaces -> applications -> agent_kernel / adapters
applications -> agent_kernel / adapters
adapters -> agent_kernel.contracts / Core Protocol
agent_kernel -> agent_kernel.contracts
agent_kernel -X-> adapters / applications / interfaces
```

禁止：

- Core 直接导入 Provider SDK、数据库驱动或具体 Tool Backend。
- Adapter 反向注入实现类型到公共 Schema。
- Application 通过内部路径绕过公开契约。
- 测试从物理实现路径导入以替代公共 API 验证。
- 创建 `core/`、`kernel/` 或其他与 `agent_kernel/` 平行的第二个核心包。

## 5. 测试组织

| 测试目录 | 证明内容 | 允许依赖 |
|---|---|---|
| `tests/unit/` | 单模块确定性规则、Schema、状态和错误 | `agent_kernel`，可使用受控替身 |
| `tests/contract/` | Adapter 遵守公共 Protocol | `agent_kernel.contracts`、对应 Adapter |
| `tests/integration/` | 多模块数据流、失败和取消传播 | Application Composition Root、真实或受控 Adapter |
| `tests/architecture/` | 导入方向、Provider 隔离和公开 API | 源码 AST、导入图、包元数据 |
| `tests/real_dialogue/` | 真实 Provider 下的 RD 场景和证据 | Application、真实 Adapter、证据工具 |
| `tests/support/` | 测试工厂、固定数据和证据辅助 | 不得被生产 Kernel 导入 |

测试目录不按实现文件镜像全部内部结构；只有当测试需要表达模块边界或验收出口时才建立对应子目录。

## 6. A3 验收清单

| 检查项 | 当前结论 |
|---|---|
| 使用 `src/agent_kernel` 作为唯一 Kernel 包 | 已形成方案 |
| 六个 Core 没有平行包 | 已形成方案 |
| Adapter、Application、Interface 与 Kernel 分离 | 已形成方案 |
| Core 不反向依赖外部层 | 已形成方案 |
| 公共入口和内部路径已区分 | 已形成方案 |
| Unit、Contract、Integration、Architecture、RD 测试分层 | 已形成方案 |
| 旧项目入口、旧协议和旧目录未迁移 | 已满足 |
| 尚未创建 Kernel 代码目录 | 已满足 |
| A3 用户任务结果确认 | 已确认 |

## 7. 后续影响

A3 方案确认后，进入 A4：

1. 创建 `pyproject.toml` 和 `uv.lock`。
2. 创建 `src/agent_kernel`、Adapter 命名空间和测试基座。
3. 建立 Architecture Test，验证本记录中的导入方向。
4. 不在 A4 标记任何 Core 模块完成。

A3 不改变六个 Core 的逻辑边界、公共类型策略或运行链路，因此不创建新的架构版本正文；如最终目录方案改变系统边界，应重新执行版本判定。
