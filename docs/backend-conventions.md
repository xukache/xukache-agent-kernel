# 后端开发规范

## 项目形态

本项目是 Python 3.11 后端 Agent Harness，当前以 CLI 为入口。Native Runtime 已实现，LangGraph 将在框架中立协议完成后作为默认可替换运行时接入。

## 环境管理

- 统一使用 `uv` 管理 Python、虚拟环境、依赖和命令运行。
- Python 固定为 3.11，使用 `.python-version`。
- 不把 `pip install`、裸 `python` 或 `python -m pytest` 写成项目主路径命令。
- 新增依赖前说明用途、隔离层、可替换性和最小 extra，避免为单个 provider 安装无关集成包。

## 本地命令

```bash
uv python pin 3.11
uv sync --extra dev
uv run pytest -v
uv run ananhu-agent version
uv run ananhu-agent ask "四川十级工伤，月工资6000，大概能赔多少钱？"
uv run ananhu-agent eval data/eval/eval_cases.jsonl
```

## 目标模块边界

```text
ananhu_agent/
  domain/               # 纯业务实体、值对象和规则
  application/          # 用例、阶段服务、状态转换、响应组装
  ports/                # Runtime、Model、Knowledge、Capability、Storage 端口
  runtimes/
    native/             # 当前 orchestrator 的演进实现
    langgraph/          # LangGraph 专有图、node 和 mapper
  infrastructure/       # 模型、检索、存储、观测适配
  interfaces/           # CLI 和未来外部入口
```

迁移采用小任务增量完成。现有 `agents/`、`orchestrator/`、`tools/` 等目录在对应端口落地前继续有效，不做一次性目录搬迁。

## 依赖规则

- `domain` 不依赖框架、SDK、CLI、数据库和网络。
- `application` 只依赖 domain 和 ports。
- runtime 与 infrastructure 实现 ports，不能反向成为业务层依赖。
- LangGraph 类型只允许出现在 `runtimes/langgraph/` 和组合根。
- 当前 CLI 和 EvalRunner 仍装配 `AgentOrchestrator`；完成任务 29 后改为依赖 `WorkflowRuntime`，不直接实例化具体图节点。

## Runtime 迁移规则

- 当前 `AgentOrchestrator` 视为 Native Runtime，不再作为永久唯一状态推进方。
- 当前运行时仍使用共享 `AgentContext` 和 `AgentMessage`；任务 26-29 完成后迁移到 `WorkflowState` 和 `StatePatch`。
- 目标状态转换和 reducer 使用普通 Python 纯函数，可脱离 LangGraph 测试。
- 目标节点返回 `StatePatch`，不得原地修改共享状态。
- 不允许把完整 Native orchestrator 包在单个 LangGraph 节点中。
- 首个 LangGraph 实现保持串行，不提前启用复杂并行、interrupt 或 checkpoint。
- Native 与 LangGraph Runtime 必须执行同一 contract tests。

## Agent 规则

- Agent 无状态，只读取项目输入并返回项目结构化输出。
- Agent 不直接写 session/case/run state。
- Agent 不直接调用工具、模型 SDK、向量库或 LangGraph API。
- Agent 不拼接完整 Prompt。
- 新 Agent 必须有独立目标、上下文、权限或专项评测理由。

## Capability 规则

- 所有能力通过 `ToolExecutor` 或后续 `CapabilityGateway`。
- 能力声明输入输出 schema、版本、风险、权限、超时、重试和幂等等级。
- 结果使用结构化 `CapabilityResult`，关键字段不得只存在于自然语言文本。
- 框架 tool adapter 只能转发到执行网关，不能绕过治理。

## Prompt 与 Context 规则

- Prompt 模板独立存储并包含 ID、版本、模型 profile、输出 schema 和 failure policy。
- ContextManager 负责 section 顺序、token 预算、Evidence/Memory 选择和构建报告。
- 当前请求、已确认事实和关键证据不得静默裁剪。
- Prompt、Context、Memory 公共协议不导入 LangGraph message 类型。

## 异步规则

- 模型、检索、存储和能力执行优先定义 async 接口。
- 不在 domain 中创建 task、event loop 或网络客户端。
- 同步 CLI 可在组合根适配 async 用例。
- 并行执行前必须验证分支无前置依赖、共享同一事实版本且 reducer 可确定合并。

## 注释和类型

- 关键模块使用中文注释说明职责、边界和非显而易见规则。
- 不给简单赋值和字段写机械注释。
- 端口、状态和运行证据使用明确类型，避免跨层传递无约束 `dict`。
- 所有持久化协议包含 `schema_version`。

## 测试与验证

- 纯领域规则和 reducer 使用单元测试。
- Agent、Capability、Repository 和 Runtime 使用 contract tests。
- Native/LangGraph 使用相同 fixture 验证结果、StopReason、能力调用和 trace。
- Fake Model 用于确定性回归；真实 provider smoke 显式 opt-in，结果单独报告。
- 文档任务至少运行 Markdown 链接/旧口径扫描和现有全量测试，确认文档没有把未实现能力写成已完成。
