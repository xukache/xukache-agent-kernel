# 安安虎 CLI MVP Agent Harness 历史实现记录

> **状态：已归档，只读，不可执行。**
>
> 2026-07-09 的任务 1-24 已完成并合并到 `mvp`。原任务 25-31 是未执行的 Agno 接入草案，已经删除并作废。任何后续开发必须使用 `2026-07-10-framework-neutral-langgraph-evolution.md`，不得根据本文创建任务分支或安装依赖。

## 历史目标

建立一个无外部 API、以 CLI 为入口的工伤咨询离线 Agent Harness，跑通意图、路由、工具、聚合、安全、trace、badcase 和 eval 闭环。

## 已完成阶段

| 阶段 | 已完成任务 | 结果 |
|---|---|---|
| P1 工程基线 | 1-3 | Python 3.11、uv、Typer、Pydantic、JSONL 证据存储 |
| P2 规则与上下文 | 4-5 | 槽位规则、PromptManager、ContextManager |
| P3 能力治理 | 6-7 | ToolRegistry、ToolExecutor、fixture RAG、确定性测算 |
| P4 Agent 闭环 | 8-11 | Fake Model、四 Agent、聚合、安全、Native Orchestrator |
| P5 CLI 与评测 | 12-14 | ask、eval、metrics、badcase 和文档 |
| P6 多轮与治理 | 15-22 | chat、session、feedback、自动 badcase、工具/安全增强、30+ eval cases |
| P7 配置与历史适配 | 23-24 | Model profile 路由、Agno-compatible 透传适配层 |

## 当前解释

- `AgentOrchestrator` 是当前 Native Runtime 的历史实现，不是永久唯一调度器。
- 四个 Agent 是 MVP 实现现状，不是未来必须固定的模块清单。
- `agno_adapters/` 是任务 24 产生的兼容层，不代表安装或使用了 Agno SDK，也不是未来主运行时。
- fake model 和 fixture RAG 只证明离线协议与工程链路可回归，不代表真实业务质量。
- 当前架构事实以 `TECH_ARCHITECTURE_MVP.md` 和 `docs/architecture/` 为准。

## 历史验收证据

- `uv run pytest -v`：53 项测试通过（2026-07-10 文档调整前后均验证）。
- CLI `ask`、`chat`、`eval` 和反馈相关命令已实现。
- Trace、SessionState、RunReport、Badcase 和分层 Eval 已有代码与测试。

## 作废内容

以下内容从未执行，且不再属于路线图：

- 安装 Agno SDK 或 AgentOS。
- 创建 Agno 专属模型客户端。
- 使用 Agno Agent 直接驱动工具调用。
- 以 Agno Team/Workflow 作为主编排器。

替代路线是先建立项目自己的状态、状态增量、能力、trace 和 Runtime 端口，再接入可替换的 LangGraph Runtime。
