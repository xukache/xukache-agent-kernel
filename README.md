# 安安虎工伤智能助手 Agno CLI MVP

安安虎工伤智能助手是一个面向工伤认定、劳动能力鉴定、待遇测算和政策咨询场景的后端型 Agent CLI 项目。当前项目不使用 Dify，基于 Agno 多 Agent 编排思路自研，MVP 阶段优先跑通无前端、无 HTTP API 的交互式 CLI 闭环。

> 当前状态：项目处于 MVP 实现阶段。仓库已初始化 Python 包、CLI 版本命令和运行时协议 schema；完整业务 Agent、RAG、测算工具、trace 存储、badcase 和 eval 闭环仍按计划逐步实现。

## 项目目标

MVP 目标是跑通以下最小闭环：

```text
用户输入
  -> 意图识别
  -> Agent 路由
  -> RAG / 测算工具
  -> 聚合校验
  -> CLI 输出
  -> Trace / Badcase / Eval
```

项目面向以下典型场景：

- 工伤认定政策咨询，例如“上班路上发生交通事故能不能认定工伤？”
- 劳动能力鉴定材料和办理路径咨询。
- 工伤待遇测算，例如“四川十级工伤，月工资 6000，大概能赔多少钱？”
- 多地政策差异、引用依据和办事风险提示。

## MVP 范围

MVP 只保留 4 个核心 Agent：

| Agent | 职责 |
|---|---|
| `IntentRouterAgent` | 意图识别、槽位抽取、低置信度追问 |
| `PolicyRAGAgent` | 法规、地方政策、办事指南检索和依据组织 |
| `DomainConsultationAgent` | 工伤认定、劳动能力鉴定、参保认定等文本政策咨询 |
| `PaymentCalculationAgent` | 工伤待遇测算解释和计算工具调用 |

MVP 明确不做：

- 前端页面。
- HTTP API / WebSocket。
- Dify 接入。
- 复杂异步任务平台。
- 并行 Agent 仲裁。
- 语音、图片、多模态输入。
- 为展示“多 Agent”而提前拆分专项 Agent。

## 技术栈

- Python：固定 `3.11`
- 环境与依赖管理：`uv`
- CLI：Typer
- 数据协议：Pydantic
- 配置与模板：PyYAML、Pydantic Settings
- 测试：pytest
- Agent 编排方向：Agno
- 本地数据形态：JSONL、fixture RAG 数据

## 快速开始

### 环境要求

- Python 3.11
- uv

### 安装依赖

```bash
uv python pin 3.11
uv sync --extra dev
```

### 运行测试

```bash
uv run pytest -v
```

### 查看 CLI 版本

```bash
uv run ananhu-agent version
```

预期输出：

```text
ananhu-agent 0.1.0
```

### 后续 MVP 命令

以下命令是 MVP 目标命令，完整业务链路实现后必须保持可用：

```bash
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```

## 项目结构

当前已实现与规划结构如下：

```text
ananhu_agent/
  cli/                 # CLI 入口和命令解析
  schemas.py           # Agent、Tool、Trace、TaskState、Report、Eval 等运行时协议
  orchestrator/        # 规划：AgentOrchestrator、路由和运行时控制
  agents/              # 规划：4 个 MVP Agent
  context/             # 规划：ContextManager、槽位合并、上下文裁剪
  prompts/             # 规划：PromptManager 和版本化 prompt 模板
  tools/               # 规划：ToolRegistry、ToolExecutor、业务工具
  models/              # 规划：ModelRouter、FakeModel、模型客户端适配
  storage/             # 规划：Trace、TaskState、Report、Badcase、Eval 存储
  evaluation/          # 规划：eval runner 和指标计算
  config/              # 规划：Pydantic Settings 和本地路径配置
docs/
  architecture.md      # 技术架构入口
  api-contracts.md     # API 契约入口，当前声明暂无公开 API
  backend-conventions.md
  architecture/        # 架构分册
tests/                 # 单元测试与垂直切片测试
```

## 核心架构原则

1. `AgentOrchestrator` 是唯一状态推进方。
2. Agent 保持无状态，只读取 `AgentContext` 并返回 `AgentMessage`。
3. Agent 不直接调用底层工具，必须通过 `ToolExecutor`。
4. Agent 不直接拼接完整 prompt，必须通过 `PromptManager` 和 `ContextManager`。
5. Prompt 必须版本化、可评测、可回滚。
6. 工具、Prompt、上下文、模型调用、校验和安全守卫必须写入 trace。
7. Trace、TaskState、RunReport 是运行证据链，不是附属日志。
8. 关键代码模块必须写中文注释，说明模块职责、协议边界、关键流程和非显而易见的业务规则。

## 文档索引

建议按以下顺序阅读：

| 文档 | 说明 |
|---|---|
| `AGENTS.md` | Agent 工作约束、分支流程和项目强制规范 |
| `docs/architecture.md` | 技术架构总纲 |
| `docs/architecture/00-overview.md` | 项目定位、MVP 范围和非目标 |
| `docs/architecture/01-business-flow.md` | 业务流程、数据流和 badcase 回流 |
| `docs/architecture/02-agent-runtime.md` | Agent 编排、上下文协议和异步边界 |
| `docs/architecture/03-prompt-context.md` | Prompt 与上下文工程 |
| `docs/architecture/04-tools-models.md` | 工具、模型和 ToolExecutor 治理 |
| `docs/architecture/05-data-observability.md` | Trace、Report、Badcase 和 Eval |
| `docs/architecture/10-evolution-rules.md` | Agent 变更监控和架构演进规则 |
| `docs/backend-conventions.md` | 后端开发规范 |
| `docs/api-contracts.md` | API 契约状态，当前暂无公开 API |

## 开发规范

- 所有 Python 环境、依赖安装、测试和 CLI 运行必须通过 `uv` 执行。
- 不把 `pip install`、`python -m pytest` 作为主路径命令写入文档或脚本。
- 每个开发任务必须从版本分支创建任务分支。
- 未经确认，不得直接合并到 `mvp`、`main`、`master` 或其他版本分支。
- 修改 Agent 清单、上下文协议、Prompt、Tool、数据模型或评测指标时，必须同步更新对应架构文档。
- 修改架构级事实时，必须更新 `docs/architecture/99-changelog.md`。
- 当前不创建前端规范，不创建空 API 领域分册。

## 测试策略

当前测试覆盖：

- 包版本与 CLI `version` 命令。
- Agent、Tool、Trace、TaskState、RunReport 等运行时协议 schema。

后续实现阶段需要继续覆盖：

- Intent / slot schema 校验。
- ToolExecutor 参数校验、错误码和 trace。
- PromptManager 模板解析和版本选择。
- ContextManager 分区裁剪，确保不裁剪当前问题。
- PolicySafetyGuard 高风险表达拦截。
- Eval runner 指标输出和 badcase 回流。

## 路线图

- P1：Python 工程与 CLI 入口。
- P2：运行时协议 schema。
- P3：上下文、PromptManager、模型路由。
- P4：ToolRegistry、ToolExecutor、RAG 与待遇测算工具。
- P5：4 个 MVP Agent 与 Orchestrator 垂直链路。
- P6：eval、badcase、运行报告和文档同步。

## 免责声明

本项目输出仅用于工伤政策咨询、材料准备和待遇测算辅助，不构成法律意见、行政决定或最终赔付承诺。实际认定、鉴定和待遇结果以当地人社部门、社保经办机构、劳动能力鉴定委员会以及现行有效法律法规为准。

---

# Ananhu Work Injury Assistant Agno CLI MVP

Ananhu Work Injury Assistant is a backend-oriented Agent CLI project for work injury recognition, labor capacity assessment, benefit calculation, and policy consultation. It does not use Dify. The MVP is designed around a custom Agno-style multi-agent orchestration architecture, with a CLI-first workflow and no frontend or public HTTP API.

> Current status: the project is in MVP implementation. The repository already contains the Python package skeleton, CLI version command, and runtime schema layer. The full business agent chain, RAG tools, calculation tools, trace storage, badcase loop, and eval loop are being implemented incrementally.

## Project Goal

The MVP aims to complete the following minimal runtime loop:

```text
User input
  -> intent recognition
  -> agent routing
  -> RAG / calculation tool
  -> aggregation and validation
  -> CLI output
  -> Trace / Badcase / Eval
```

Typical use cases include:

- Work injury recognition consultation.
- Labor capacity assessment materials and process guidance.
- Work injury benefit estimation.
- Local policy differences, citations, and risk reminders.

## MVP Scope

The MVP keeps only 4 core agents:

| Agent | Responsibility |
|---|---|
| `IntentRouterAgent` | Intent recognition, slot extraction, and clarification for low-confidence inputs |
| `PolicyRAGAgent` | Retrieval and organization of laws, local policies, and service guides |
| `DomainConsultationAgent` | Text-based policy consultation for recognition, assessment, and insurance-related topics |
| `PaymentCalculationAgent` | Benefit calculation explanation and calculation tool orchestration |

The MVP explicitly excludes:

- Frontend UI.
- HTTP API / WebSocket.
- Dify integration.
- Complex async task platform.
- Parallel agent arbitration.
- Voice, image, or multimodal input.
- Prematurely splitting domain-specific agents just to demonstrate multi-agent design.

## Tech Stack

- Python: fixed at `3.11`
- Environment and dependency management: `uv`
- CLI: Typer
- Runtime schemas: Pydantic
- Configuration and templates: PyYAML, Pydantic Settings
- Testing: pytest
- Agent orchestration direction: Agno
- Local data format: JSONL and fixture RAG data

## Quick Start

### Requirements

- Python 3.11
- uv

### Install Dependencies

```bash
uv python pin 3.11
uv sync --extra dev
```

### Run Tests

```bash
uv run pytest -v
```

### Check CLI Version

```bash
uv run ananhu-agent version
```

Expected output:

```text
ananhu-agent 0.1.0
```

### Planned MVP Commands

The following commands are target MVP commands and must remain available after the full business flow is implemented:

```bash
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```

## Repository Layout

```text
ananhu_agent/
  cli/                 # CLI entrypoints and command parsing
  schemas.py           # Runtime protocols for Agent, Tool, Trace, TaskState, Report, and Eval
  orchestrator/        # Planned: AgentOrchestrator, routing, and runtime control
  agents/              # Planned: 4 MVP agents
  context/             # Planned: ContextManager, slot merge, and context trimming
  prompts/             # Planned: PromptManager and versioned prompt templates
  tools/               # Planned: ToolRegistry, ToolExecutor, and business tools
  models/              # Planned: ModelRouter, FakeModel, and model client adapters
  storage/             # Planned: Trace, TaskState, Report, Badcase, and Eval storage
  evaluation/          # Planned: eval runner and metric calculation
  config/              # Planned: Pydantic Settings and local path configuration
docs/
  architecture.md      # Architecture entrypoint
  api-contracts.md     # API contract entrypoint; currently no public API
  backend-conventions.md
  architecture/        # Architecture chapters
tests/                 # Unit tests and vertical slice tests
```

## Architecture Principles

1. `AgentOrchestrator` is the only component that advances runtime state.
2. Agents are stateless. They read `AgentContext` and return `AgentMessage`.
3. Agents must not call low-level tools directly; all calls go through `ToolExecutor`.
4. Agents must not assemble full prompts directly; prompts go through `PromptManager` and `ContextManager`.
5. Prompts must be versioned, evaluable, and rollbackable.
6. Tool calls, prompts, context, model calls, validation, and safety checks must be recorded in trace.
7. Trace, TaskState, and RunReport are runtime evidence, not auxiliary logs.
8. Key code modules must include Chinese comments explaining module responsibilities, protocol boundaries, key flows, and non-obvious business rules.

## Documentation

Recommended reading order:

| Document | Description |
|---|---|
| `AGENTS.md` | Agent working rules, branch workflow, and project constraints |
| `docs/architecture.md` | Architecture overview |
| `docs/architecture/00-overview.md` | Project positioning, MVP scope, and non-goals |
| `docs/architecture/01-business-flow.md` | Business flow, data flow, and badcase feedback loop |
| `docs/architecture/02-agent-runtime.md` | Agent orchestration, context protocol, and async boundary |
| `docs/architecture/03-prompt-context.md` | Prompt and context engineering |
| `docs/architecture/04-tools-models.md` | Tool, model, and ToolExecutor governance |
| `docs/architecture/05-data-observability.md` | Trace, Report, Badcase, and Eval |
| `docs/architecture/10-evolution-rules.md` | Agent evolution and architecture change rules |
| `docs/backend-conventions.md` | Backend development conventions |
| `docs/api-contracts.md` | API contract status; currently no public API |

## Development Rules

- Use `uv` for Python environment management, dependency installation, tests, and CLI commands.
- Do not use `pip install` or `python -m pytest` as the primary documented path.
- Create a task branch from the current version branch for every development task.
- Do not merge into `mvp`, `main`, `master`, or other version branches without confirmation.
- When changing agent lists, context protocols, prompts, tools, data models, or eval metrics, update the corresponding architecture documents.
- Architecture-level changes must be recorded in `docs/architecture/99-changelog.md`.
- Do not create frontend conventions or empty API contract chapters during the current CLI-only MVP phase.

## Testing Strategy

Current tests cover:

- Package version and CLI `version` command.
- Runtime schemas for Agent, Tool, Trace, TaskState, and RunReport.

Future implementation should cover:

- Intent and slot schema validation.
- ToolExecutor parameter validation, error codes, and trace.
- PromptManager template parsing and version selection.
- ContextManager section trimming while preserving the current query.
- PolicySafetyGuard blocking of unsafe expressions.
- Eval runner metrics and badcase feedback.

## Roadmap

- P1: Python project and CLI entrypoint.
- P2: Runtime protocol schemas.
- P3: Context, PromptManager, and model routing.
- P4: ToolRegistry, ToolExecutor, RAG, and benefit calculation tools.
- P5: 4 MVP agents and the orchestrator vertical flow.
- P6: Eval, badcase, run reports, and documentation synchronization.

## Disclaimer

This project provides assistance for work injury policy consultation, document preparation, and benefit estimation. It does not constitute legal advice, an administrative decision, or a guaranteed compensation result. Final recognition, assessment, and benefit outcomes are subject to local authorities, social insurance agencies, labor capacity assessment committees, and currently effective laws and regulations.
