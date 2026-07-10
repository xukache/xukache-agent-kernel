# 安安虎工伤智能助手 Agent Harness

安安虎工伤智能助手是面向工伤认定、劳动能力鉴定、待遇辅助测算和政策咨询的 Python 后端 Agent Harness。项目当前以 CLI 作为开发和验收入口，默认运行时为 `NativeWorkflowRuntime`，通过框架中立 `WorkflowRuntime` 端口调用。

当前代码已经具备离线可回归闭环：CLI、MVP Agent、Prompt/上下文管理、CapabilityGateway、fixture 政策检索、确定性待遇测算、JSONL trace、badcase 和 eval。LangGraph 尚未接入；后续接入时只作为可替换运行时，不拥有业务状态、能力治理、Prompt、trace 或 eval 协议。

## 当前状态

- Python 版本：3.11。
- 环境和命令管理：`uv`。
- Python 发行包名：`ananhu-agent`。
- CLI 命令：`ananhu-agent`。
- 当前外部入口：CLI；没有 HTTP API、WebSocket 或前端。
- 当前模型和政策检索以 fake/fixture 为主，用于验证协议和离线工程闭环，不代表真实模型和真实政策语料的生产验收。

## 快速开始

```bash
uv python pin 3.11
uv sync --extra dev
uv run ananhu-agent version
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
uv run pytest -v
```

## 常用命令

```bash
# 单轮咨询
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"

# 交互式会话
uv run ananhu-agent chat

# 运行评测
uv run ananhu-agent eval data/eval/eval_cases.jsonl

# 查看版本
uv run ananhu-agent version
```

运行证据默认写入 `.ananhu-runtime/`，包括 trace、运行报告和 badcase 记录。

## 项目结构

```text
ananhu_agent/
  agents/          # 当前 MVP Agent 实现
  capabilities/    # CapabilityRequest / CapabilityResult / CapabilityGateway
  cli/             # Typer CLI 入口
  context/         # 上下文构建和槽位规则
  evaluation/      # eval runner 和指标
  models/          # 模型 profile、路由和 fake model
  orchestrator/    # 聚合、规则、安全校验和 badcase 规则
  prompts/         # 版本化 Prompt
  runtime.py       # 默认 Runtime 组合根
  runtimes/native/ # 当前默认 Native Runtime
  storage/         # JSONL 存储和运行证据
  tools/           # ToolRegistry、ToolExecutor 和业务工具
  workflow/        # RunRequest、WorkflowState、StatePatch、Reducer、WorkflowResult
data/
  eval/            # 离线评测用例
docs/
  architecture.md  # 架构事实源入口
tests/
```

## 文档入口

| 文档 | 说明 |
|---|---|
| `AGENTS.md` | 开发约束、分支流程和文档同步纪律 |
| `TECH_ARCHITECTURE_MVP.md` | 技术架构版本入口 |
| `docs/architecture.md` | 当前架构事实源入口 |
| `docs/backend-conventions.md` | 后端开发规范 |
| `docs/api-contracts.md` | 当前外部 API 状态和启用条件 |

详细架构以 `docs/architecture.md` 及其分册为准，README 只保留项目入口信息。

## 当前非目标

- 不提供 HTTP API、WebSocket、SSE、前端或小程序入口。
- 不把当前四个 Agent 固化为永久架构边界。
- 不把 LangGraph 类型引入 domain、application、Agent、Capability、Prompt、Trace 或 Eval 公共协议。
- 不把 fake model、fixture RAG 的通过率描述为真实业务效果。

## 免责声明

本项目输出仅用于工伤政策咨询、材料准备和待遇辅助测算，不构成法律意见、行政决定或最终赔付承诺。实际认定、鉴定和待遇结果以当地主管部门、经办机构以及现行有效法律法规为准。
