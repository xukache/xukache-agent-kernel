# 安安虎工伤智能助手 Agent Harness

安安虎工伤智能助手是面向工伤认定、劳动能力鉴定、待遇辅助测算和政策咨询的 Python 后端 Agent Harness。项目当前以 CLI 作为开发和验收入口，默认运行时为 `LangGraphWorkflowRuntime`，通过框架中立 `WorkflowRuntime` 端口调用。

当前代码已经具备离线可回归闭环：CLI、MVP Agent、Prompt/上下文管理、CapabilityGateway、ModelGateway、fixture 政策检索、确定性待遇测算、JSONL trace、badcase、eval，以及 Native/LangGraph 双运行时差分验收。LangGraph 只作为可替换运行时，不拥有业务状态、能力治理、Prompt、trace 或 eval 协议。

## 当前状态

- Python 版本：3.11。
- 环境和命令管理：`uv`。
- Python 发行包名：`ananhu-agent`。
- CLI 命令：`ananhu-agent`。
- 当前外部入口：CLI；没有 HTTP API、WebSocket 或前端。
- 模型默认使用 Fake，可显式切换通用 OpenAI-compatible provider；政策检索仍使用 fixture。这些能力不代表真实咨询链路的生产验收。

## 快速开始

```bash
uv python pin 3.11
uv sync --extra dev
uv run ananhu-agent version
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
uv run ananhu-agent eval data/eval/eval_cases.jsonl --runtime both
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

# 双运行时差分验收
uv run ananhu-agent eval data/eval/eval_cases.jsonl --runtime both

# 查看版本
uv run ananhu-agent version
```

### Chat 交互

- 输入 `/` 打开命令候选列表。
- 上下键移动候选，`Tab` 补全到输入框，`Enter` 提交当前输入，`Esc` 收起候选。
- `F1` 帮助、`F2` 上下文、`F3` trace、`F4` 反馈。
- `Ctrl+N` 新会话、`Ctrl+L` 清屏、`Ctrl+R` 重试、`Ctrl+C` 取消或退出。
- `/context` 显示当前 session 的当前事实和本次 chat 进程内已完成轮次摘要。
- `/new` 会重置 session；重启 `chat` 也会创建新的 session。

运行证据默认写入 `.ananhu-runtime/`，包括 trace、运行报告和 badcase 记录。双运行时差分额外写入 `runtime-differential.json`。

## 真实模型配置

默认配置不会读取 key 或访问网络。切换 OpenAI-compatible provider 时集中配置模型 profile，
密钥不会进入 profile、trace 或评测产物：

```bash
export ANANHU_MODEL_API_KEY="..."
export ANANHU_MODEL_BASE_URL="https://provider.example/v1"
export ANANHU_MODELS='{"intent_fast":{"provider":"openai_compatible","model":"provider-model","temperature":0,"timeout_seconds":30}}'

uv run ananhu-agent ask "工伤认定需要哪些条件？"
```

真实连接 smoke 默认跳过，需显式启用并单独指定模型：

```bash
ANANHU_REAL_MODEL_SMOKE=1 \
ANANHU_REAL_MODEL="provider-model" \
uv run pytest tests/test_model_gateway_contract.py -v
```

## 项目结构

```text
ananhu_agent/
  agents/          # 当前 MVP Agent 实现
  capabilities/    # CapabilityRequest / CapabilityResult / CapabilityGateway
  cli/             # Typer CLI 入口
  context/         # 上下文构建和槽位规则
  evaluation/      # eval runner 和指标
  models/          # 模型 profile 与 gateway 路由
  ports/           # ModelGateway 等框架中立端口
  infrastructure/  # OpenAI-compatible、Fake 等基础设施适配器
  orchestrator/    # 聚合、规则、安全校验和 badcase 规则
  prompts/         # 版本化 Prompt
  runtime.py       # 默认 Runtime 组合根
  runtimes/native/ # 显式回归 Native Runtime
  runtimes/langgraph/ # 当前默认 LangGraph Runtime
  storage/         # JSONL 存储和运行证据
  tools/           # 保留的领域 handler；能力治理统一位于 capabilities/
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
