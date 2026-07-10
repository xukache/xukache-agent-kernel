# 安安虎工伤智能助手 Agent Harness

安安虎工伤智能助手是面向工伤认定、劳动能力鉴定、待遇辅助测算和政策咨询的后端 Agent 系统。项目当前以 CLI 作为开发和验收入口，已经具备可离线回归的四 Agent MVP、工具治理、Prompt/上下文管理、JSONL 运行证据、badcase 和 eval 闭环。

下一阶段采用 **LangGraph 默认运行时 + 框架中立业务内核**：LangGraph负责工作流调度，项目自己掌握领域状态、Agent/Tool 协议、检索证据、Prompt、trace、usage 和评测，避免更换编排框架时业务不可用。

## 当前状态

- Python 3.11 + `uv` 工程已初始化。
- CLI `ask`、`chat`、`eval` 和反馈相关命令已实现。
- 当前 `AgentOrchestrator` 是已实现的 Native Runtime，不是长期唯一调度器。
- 当前四个 Agent 是 MVP 实现现状，不是永久模块边界。
- 当前模型和政策检索以确定性 fake/fixture 为主，验证的是协议和离线工程闭环，不代表真实模型与真实政策语料已经完成生产验收。
- LangGraph 尚未接入；必须先完成框架中立状态和运行时端口，再引入依赖。

## 当前 Native MVP 链路

```text
请求
  -> 意图与槽位抽取
  -> 规则修正和缺失槽位判断
  -> 四 Agent 串行路由
  -> fixture 政策检索 / 确定性待遇测算
  -> 引用、结果和安全校验
  -> CLI 答复
  -> Trace / TaskState / RunReport / Badcase / Eval
```

目标稳定业务阶段将在任务 26-31 中演进为案件事实、可信 jurisdiction、CapabilityGateway、证据校验、Usage 和双 Runtime 链路，当前代码尚未具备全部目标协议。

## 架构原则

1. 业务流程由稳定阶段定义，不按 Agent 名称机械建图。
2. LangGraph 负责调度，项目 reducer/transition policy 负责业务状态合并语义。
3. Agent 无状态，只返回项目定义的结构化结果或状态增量。
4. 当前外部能力经过 `ToolExecutor` 处理注册、schema、调用方、超时、重复调用和 trace；目标 `CapabilityGateway` 再补齐稳定幂等、重试、脱敏、jurisdiction 和 usage。
5. 案件事实、知识证据、会话记忆和 checkpoint 分离管理。
6. Prompt、上下文、模型、知识库和工具均版本化并进入运行证据。
7. 项目 trace 是审计和评测事实源，框架观测只能作为补充。
8. Native Runtime 与 LangGraph Runtime 必须通过同一套 contract tests 和 eval 数据。

## LangGraph 边界

LangGraph可以负责节点连接、条件路由、中断恢复、节点重试和必要的有限并行，但不能拥有以下语义：

- 工伤案件事实、地市权限和政策适用性。
- Agent、Tool、Prompt、Evidence 和 Response 公共协议。
- session/case/run ID 规则。
- trace、usage、badcase 和 eval schema。
- 业务错误码、停止原因和工具幂等策略。

详细边界见 `docs/architecture/02-agent-runtime.md`。

## 快速开始

```bash
uv python pin 3.11
uv sync --extra dev
uv run pytest -v
uv run ananhu-agent version
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```

## 项目结构

```text
ananhu_agent/
  agents/              # 当前 MVP Agent 实现
  orchestrator/        # 当前 Native Runtime、聚合、规则和安全校验
  context/             # 上下文构建和槽位规则
  prompts/             # 版本化 Prompt
  tools/               # ToolRegistry、ToolExecutor 和业务能力
  models/              # 模型 profile、路由和测试替身
  storage/             # session、trace、report、badcase 存储
  evaluation/          # eval runner 和分层指标
  agno_adapters/       # 已完成任务 24 的历史兼容层，非未来主运行时
docs/
  architecture.md
  architecture/
  api-contracts.md       # 当前外部 API 状态和启用条件
  backend-conventions.md # Python 后端规范
tests/
```

目标结构将在后续任务中增量演进为 `domain/`、`application/`、`ports/`、`runtimes/native/`、`runtimes/langgraph/` 和 `infrastructure/`，不会在一次任务中整体搬迁。

## 文档索引

| 文档 | 说明 |
|---|---|
| `AGENTS.md` | 开发约束、分支流程和文档同步纪律 |
| `TECH_ARCHITECTURE_MVP.md` | 当前 MVP 技术架构基线 |
| `docs/architecture.md` | 架构事实源入口和阅读顺序 |
| `docs/architecture/00-overview.md` | 定位、范围和分层 |
| `docs/architecture/01-business-flow.md` | 业务阶段和数据流 |
| `docs/architecture/02-agent-runtime.md` | Native/LangGraph 运行时、状态和恢复边界 |
| `docs/architecture/03-prompt-context.md` | Prompt、上下文和记忆治理 |
| `docs/architecture/04-tools-models.md` | 能力执行、模型和知识检索治理 |
| `docs/architecture/05-data-observability.md` | Trace、Usage、Badcase 和 Eval |
| `docs/architecture/10-evolution-rules.md` | 架构演进约束 |
| `docs/backend-conventions.md` | Python 后端规范 |
| `docs/api-contracts.md` | 当前外部 API 状态和启用条件 |

## 当前非目标

- 当前任务不实现 HTTP API、WebSocket、前端或小程序。
- 不为了多 Agent 展示继续拆分专项 Agent。
- 不在框架中立协议完成前接入 LangGraph checkpoint 和复杂并行图。
- 不将 fake model、fixture RAG 的通过率描述为真实业务效果。

## 免责声明

本项目输出仅用于工伤政策咨询、材料准备和待遇辅助测算，不构成法律意见、行政决定或最终赔付承诺。实际认定、鉴定和待遇结果以当地主管部门、经办机构以及现行有效法律法规为准。
