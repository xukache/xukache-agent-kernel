# Agent Kernel A4 uv、pytest 与 Architecture Test 基座记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | A4：建立 uv、pytest 与 Architecture Test 基座 |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/a4-engineering-test-foundation` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | A1、A2、A3 已完成 |

本记录只建立可安装、可导入、可测试的 Python 工程基座，不实现
`Agent`、`Workflow`、`Tool`、`Memory`、`Model` 或 `Runtime`。

## 2. 任务目标

A4 将 A3 已确认的物理目录转换为最小可运行工程，并建立持续保护架构边界的测试入口：

- Python 版本固定为 3.11。
- 依赖、环境、测试和运行统一通过 `uv` 管理。
- `agent_kernel` 可以从安装后的工程导入。
- Architecture Test 使用 AST 检查静态导入边界。
- 不恢复旧项目工程文件、代码、测试或入口。
- 不创建平行 `core/`、`kernel/` 包，也不声明任何 Core 完成。

## 3. 已确认工程结构

```text
pyproject.toml
uv.lock
src/
└── agent_kernel/
    └── __init__.py
tests/
├── architecture/
│   └── test_import_boundaries.py
└── unit/
    └── test_smoke.py
```

当前不创建 `agent_kernel` 的 Core 子目录、Adapter、Application 或 Interface
实现目录。后续任务只能在对应模块逐项确认后创建代码目录。

## 4. 工程选择

### 4.1 `pyproject.toml`

- 使用 Hatchling 作为构建后端。
- 使用 `src/` layout，Wheel 只打包 `src/agent_kernel`。
- Python 要求为 `>=3.11,<3.12`，与 `.python-version` 一致。
- Pydantic 使用 `>=2.10,<3`，当前锁定版本为 2.13.4。
- pytest 使用 `>=8.3,<9`，当前锁定版本为 8.4.2。

Pydantic 在 A2 已确认的公共 Schema Model 策略中使用；A4 只锁定依赖，
不创建 Schema 实现。

### 4.2 测试入口

```bash
uv sync
uv run pytest -q
uv run pytest -q tests/architecture
uv run python -c "import agent_kernel"
```

pytest 开启 `--strict-config` 和 `--strict-markers`，避免拼写错误或未知测试
配置被静默接受。

## 5. Architecture Test 规则

`tests/architecture/test_import_boundaries.py` 使用 Python AST 解析
`src/agent_kernel/**/*.py` 的导入声明，当前检查：

1. Kernel 不导入 `applications`、`interfaces`、`adapters`、Provider SDK、
   数据库驱动或 Workflow 框架。
2. `src/` 下不存在平行 `core/` 或 `kernel/` 包。

测试使用导入图方向检查，不使用简单全文关键词禁词。随着 Adapter、
Application、Interface 和六个 Core 逐步确认，后续任务扩展同一测试入口。

## 6. 验证结果

| 命令 | 结果 |
|---|---|
| `uv lock` | 通过，解析 12 个包 |
| `uv sync` | 通过，工程 Wheel 构建并安装 |
| `uv run pytest -q` | 通过，3 passed |
| `uv run pytest -q tests/architecture` | 通过，2 passed |
| `uv run python -c "import agent_kernel; print(agent_kernel.__file__)"` | 通过，导入 `src/agent_kernel/__init__.py` |
| `uv lock --check` | 通过 |
| `git diff --check` | 通过 |

## 7. 与架构和规格的关系

- A4 不改变六个 Core、依赖方向、运行链路或公开协议，因此不创建架构版本正文。
- `DEV_SPEC.md` 的 A4 状态已在用户确认后更新为 `[x]`。
- `docs/backend-conventions.md` 已补充实际依赖版本和统一命令。
- `docs/architecture/99-changelog.md` 已记录工程基座建立事实。
- 本任务只关联 `K-009`，不声明任何模块实现完成。

## 8. 已知限制

- 目前没有 Core Protocol、Schema、Adapter 或 Application 实现。
- Architecture Test 目前只覆盖已经存在的空 Kernel 源码；后续新增模块时必须继续扩展导入图规则。
- 真实 Provider、真实对话证据和异步执行验证属于 A5 及 B-G 任务。
