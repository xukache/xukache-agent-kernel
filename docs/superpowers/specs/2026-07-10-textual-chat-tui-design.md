# Textual Chat TUI 与实时运行检查器设计

## 1. 版本与范围

| 字段 | 内容 |
|---|---|
| 状态 | 设计定稿 |
| 日期 | 2026-07-10 |
| 当前架构基线 | v0.6-model-catalog |
| 目标架构版本 | v0.7-textual-chat-tui |
| 影响入口 | `ananhu-agent chat` |

本设计将现有逐行 Typer `chat` 直接替换为 Textual TUI。`ask`、`eval`、`version` 等非交互命令保持原行为。

功能范围：

1. 为 `other` 意图提供确定性欢迎与能力范围说明，禁止空白回复。
2. 单栏展示用户消息、可折叠执行过程、AI Markdown 回复和本轮 Usage。
3. 运行期间实时更新节点、模型、工具和校验状态。
4. 每个节点和工具的输入、输出支持独立展开、收起和 JSON 高亮。
5. 使用项目自己的事件、状态和 Usage 协议，不引入 Agno Runtime 或 LangGraph 类型。

前置条件：OpenAI-compatible JSON Schema 指令、规范槽位名和省级行政区归一化修复已独立验证并合并。

## 2. 非目标

- 不展示模型隐藏思维链、内部推理 token 或供应商私有 reasoning 内容。
- 不新增 HTTP API、WebSocket、前端页面或远程调试服务。
- 不替换 `WorkflowRuntime`、项目 reducer、TraceRecorder 或 CapabilityGateway 的治理职责。
- 不在本任务实现模型流式输出；TUI 实时更新的是项目运行事件和阶段状态。
- 不保留旧 `chat` 交互模式或新增并行的 `tui` 命令。

## 3. 体验设计

### 3.1 单栏结构

界面从上到下包含：

1. 顶部状态：应用名、会话 ID、Runtime、provider 和 model。
2. 可滚动会话区：按轮次显示用户消息、执行过程、AI 消息和 Usage。
3. 固定多行输入区：`Enter` 发送，`Shift+Enter` 换行。
4. 底部状态栏：快捷键、运行状态和连接状态。

每轮结构：

```text
用户消息
└─ 执行过程（默认折叠，运行时实时更新）
   ├─ understand
   │  ├─ 节点输入
   │  ├─ 模型调用
   │  │  ├─ 模型输入
   │  │  └─ 模型输出
   │  └─ 节点输出
   ├─ merge_facts
   ├─ execute
   │  ├─ PaymentCalculationTool
   │  │  ├─ 工具输入
   │  │  └─ 工具输出
   │  └─ PolicyRAGTool
   ├─ compose
   └─ safety
AI Markdown 消息
本轮 Usage 状态行
```

### 3.2 视觉语义

- 用户消息：蓝色标识。
- AI 消息：绿色标识，使用 Textual `Markdown`。
- 意图与规范槽位：黄色。
- 模型事件：蓝色。
- 工具事件：紫色。
- 成功：绿色；运行中：spinner；失败：红色；等待：弱化灰色。
- JSON 输入输出：Rich `Syntax` 高亮，限制初始高度并支持内部滚动。

### 3.3 展开规则

- 当前运行节点自动展开，已完成节点默认收起。
- 回答完成后，整个执行过程自动收起，只显示摘要。
- 用户手动展开后，在当前轮内保持展开状态。
- 节点、模型、工具或安全校验失败时自动展开失败路径。
- 鼠标点击或键盘 `Enter` 展开、收起；`r` 切换摘要与脱敏原始 JSON。

### 3.4 快捷键

| 按键 | 行为 |
|---|---|
| `Tab` | 在输入区和执行树之间切换 |
| `Enter` | 在输入区发送；在树上展开或收起 |
| `Shift+Enter` | 输入换行 |
| `Ctrl+N` | 新会话 |
| `Ctrl+L` | 清空当前界面，不删除持久化 trace |
| `Ctrl+R` | 重试上一轮请求 |
| `Ctrl+C` | 退出 |
| `c` | 复制当前节点的脱敏 JSON |
| `r` | 切换摘要与脱敏原始 JSON |

## 4. `other` 意图

`other` 不进入政策检索、待遇测算或证据校验链路，直接返回确定性能力说明：

```text
你好，我是安安虎工伤咨询助手。你可以咨询工伤认定、劳动能力鉴定和待遇测算问题。
```

非问候类的 `other` 输入使用同一能力边界回复，并邀请用户改写为工伤相关问题。任何停止原因都必须映射到 `final_answer`、`clarification_question` 或 `error_message` 之一，CLI 不得输出空白消息。

## 5. 实时事件架构

### 5.1 数据流

```text
WorkflowRuntime
  -> 项目 TraceEvent / RunProgressEvent
       -> TraceRecorder：持久化 JSONL
       -> TuiEventSink：写入 asyncio.Queue
            -> Textual Worker
                 -> 当前轮 RunInspector
```

Textual 不读取 LangGraph event、message、checkpoint 或 channel。Native 与 LangGraph 必须产生相同的项目级运行事件，TUI 只按 `run_id`、`request_id` 和 `logical_call_id` 关联。

### 5.2 事件补充

在现有模型、工具和业务 trace 基础上补充：

- `node_started`：node、phase、attempt、脱敏输入摘要。
- `node_finished`：node、phase、attempt、耗时、`StatePatch` 摘要。
- `node_failed`：项目错误码、retryable、耗时和安全错误摘要。
- `run_finished`：停止原因、聚合 Usage、总耗时和最终状态。

节点输入输出必须采用项目 Pydantic 类型序列化后的受控视图，不能把 LangGraph state、Command 或 provider 响应放入事件。

### 5.3 Textual 并发

- TUI 使用 Textual worker 执行 async `WorkflowRuntime.invoke()`。
- 项目事件通过非阻塞 `asyncio.Queue` 推送给 UI。
- UI 更新必须在 Textual message loop 中完成。
- 单会话默认一次只运行一个请求；运行中禁止重复发送，但允许浏览历史轮次。
- `Ctrl+R` 创建新的 run/request ID，保留原失败轮次用于审计。

## 6. 输入输出与脱敏

### 6.1 默认摘要

- 节点输入：phase、已确认案件事实、意图、证据计数和能力结果计数。
- 节点输出：目标 phase、被更新字段和 append/merge 数量。
- 模型输入：Prompt ID/version、profile、schema 摘要和裁剪后的消息。
- 模型输出：结构化业务输出、finish reason、usage 和耗时。
- 工具输入输出：CapabilityGateway 治理后实际参数、结果、状态、fallback 和耗时。

### 6.2 安全规则

以下字段在摘要、原始 JSON、剪贴板和错误信息中始终移除或替换为 `***`：

- API key、Authorization、Cookie 和代理凭据。
- SecretStr 内容和环境变量值。
- provider 完整错误体中的潜在敏感字段。

长 Prompt、工具结果和文档正文按字符数与条目数裁剪，并标记原始长度。TraceRecorder 仍是完整业务证据来源，但同样遵守密钥禁止规则。

## 7. Usage 状态行

AI 消息完整输出后显示本轮所有模型调用的聚合数据：

```text
↑ 455 输入  ↓ 380 输出  Σ 835 tokens  ⚡ 104.3 tok/s  ◷ 6.1s
```

口径：

- 输入、输出、cache 和 total token 对本轮全部 `ModelResult` 求和。
- 输出速度为总输出 token / 模型调用累计耗时；无输出或 fake usage 时显示 `--`。
- 总耗时覆盖完整 Runtime，而非只计算模型调用。
- 多模型明细放在执行过程的模型节点中。
- 未报告 usage 的 provider 显示 `unknown`，禁止用字符数伪造 token。

## 8. 错误与空状态

- Provider、模型、工具、校验和安全错误使用项目错误码映射为用户可读消息。
- 失败节点自动展开；错误详情不得包含 secret 或完整敏感响应。
- 无政策证据时明确说明证据不足并给出补充方向。
- `other`、clarification、capability failure 和 safety blocked 均必须有可见消息。
- TUI 启动配置错误时显示全宽错误面板，并允许退出或重新加载本地配置。

## 9. 组件边界

建议新增或调整：

- `ananhu_agent/cli/tui/app.py`：Textual App、worker 和会话生命周期。
- `ananhu_agent/cli/tui/widgets/turn.py`：单轮用户/过程/AI/Usage 组合。
- `ananhu_agent/cli/tui/widgets/run_inspector.py`：节点、模型、工具树。
- `ananhu_agent/cli/tui/presentation.py`：事件到展示模型的纯转换、裁剪和脱敏。
- `ananhu_agent/ports/run_event_sink.py`：框架中立事件发布端口。
- `ananhu_agent/infrastructure/events/queue_sink.py`：Textual 队列适配器。
- `ananhu_agent/cli/main.py`：`chat` 改为启动 Textual App。

Rich/Textual 类型只能存在于 `cli/tui` 展示层。domain、application、Agent、Tool、Prompt、Eval 和 Runtime 公共协议不得导入 Textual。

## 10. 测试策略

1. Textual Pilot：启动、输入、发送、焦点、展开收起、新会话、重试和退出。
2. Fake Runtime：验证事件按 run/request 关联并实时更新正确轮次。
3. Contract：Native/LangGraph 产生等价的 node started/finished/failed 事件。
4. Presentation：节点、模型、工具输入输出摘要、JSON 裁剪和敏感字段脱敏。
5. Usage：单模型、多模型、fake、缺失 usage、失败调用和速度计算。
6. `other`：问候与非领域问题都有可见能力说明，且不调用政策与测算工具。
7. Error：模型、工具、证据和安全失败自动展开且没有空白消息。
8. Regression：`ask`、`eval`、双运行时差分和现有 CLI 命令保持通过。

## 11. 验收标准

- `uv run ananhu-agent chat` 直接进入 Textual TUI。
- 用户可用键盘或鼠标逐层展开每个节点、模型和工具的输入输出。
- 执行树在 Runtime 运行期间实时更新，完成后自动收起。
- AI 消息支持 Markdown，消息末尾展示本轮聚合 Usage。
- `你好` 和其他 `other` 输入不会产生空白回复。
- 节点失败自动展开并显示脱敏错误。
- 80 列窄终端不发生横向内容挤压；JSON 使用内部滚动。
- Native/LangGraph 不向 TUI 泄漏框架类型，业务 trace 仍是共同事实源。
- API key 不出现在屏幕、剪贴板、测试 fixture、trace 或 Git 中。

## 12. 已知限制

- 首版不支持模型 token 级流式输出。
- Textual TUI 需要支持 ANSI 和交互输入的终端；CI 使用 Pilot/headless 测试。
- 超大 JSON 只展示裁剪视图，完整业务证据通过受控 trace 查询。
- 复制能力取决于终端剪贴板支持；不支持时提供保存脱敏片段的替代提示。
