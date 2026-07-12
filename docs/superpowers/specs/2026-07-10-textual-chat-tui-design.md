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
5. 模型显式返回 `reasoning_content` 时，在对应模型节点下提供默认折叠的“模型思考”。
6. 使用项目自己的事件、状态和 Usage 协议，不引入 Agno Runtime 或 LangGraph 类型。

前置条件：OpenAI-compatible JSON Schema 指令、规范槽位名和省级行政区归一化修复已独立验证并合并。

## 2. 非目标

- 不推断或生成模型隐藏思维链；只展示 provider 响应中显式返回并经适配器归一化的 reasoning 内容。
- 不新增 HTTP API、WebSocket、前端页面或远程调试服务。
- 不替换 `WorkflowRuntime`、项目 reducer、TraceRecorder 或 CapabilityGateway 的治理职责。
- 不在本任务实现模型流式输出；TUI 实时更新的是项目运行事件和阶段状态。
- 不保留旧 `chat` 交互模式或新增并行的 `tui` 命令。

## 3. 体验设计

### 3.1 单栏结构

界面从上到下包含：

1. 顶部状态：应用名、会话 ID 和 Runtime；活动 provider/model 只显示在当前模型节点。
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
   │  │  ├─ 模型思考（provider 显式返回时出现）
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
- 模型思考默认保持折叠，用户明确展开后才渲染原文。
- 鼠标点击或键盘 `Enter` 展开、收起；`r` 切换摘要与脱敏原始 JSON。

### 3.4 快捷键

| 按键 | 行为 |
|---|---|
| `Tab` | 在输入区和执行树之间切换 |
| `Enter` | 在输入区发送；在树上展开或收起 |
| `Shift+Enter` / `Ctrl+J` | 输入换行；`Ctrl+J` 是不能区分 Shift+Enter 的终端后备键 |
| `Ctrl+N` | 新会话 |
| `Ctrl+L` | 清空当前界面，不删除持久化 trace |
| `Ctrl+R` | 重试上一轮请求 |
| `Ctrl+C` | 退出 |
| `r` | 切换摘要与脱敏原始 JSON |

## 4. `other` 意图

`other` 在 `plan` 阶段选择确定性无工具路径：`execute` 不产生 capability 请求，`compose` 生成能力
说明，之后仍经过 `safety` 并以 `completed` 结束。Native/LangGraph 必须产生等价事件。欢迎文案为：

```text
你好，我是安安虎工伤咨询助手。你可以咨询工伤认定、劳动能力鉴定和待遇测算问题。
```

非问候类的 `other` 输入使用同一能力边界回复，并邀请用户改写为工伤相关问题。任何停止原因都必须映射到 `final_answer`、`clarification_question` 或 `error_message` 之一，CLI 不得输出空白消息。

## 5. 实时事件架构

### 5.1 数据流

```text
WorkflowRuntime / ModelGateway / CapabilityGateway
  -> RunEventSink.publish(RunProgressEvent)
       -> TraceRecorderSink：投影为不含 transient_payload 的 TraceEvent
       -> QueueRunEventSink：原样写入同一 event loop 的 asyncio.Queue
            -> Textual Worker -> 当前轮 RunInspector
```

系统只新增一个实时协议 `RunProgressEvent`，不建立第二套业务事件总线。事件包含可持久化的
`public_payload` 和仅在当前进程存在的 `transient_payload`；后者设置 Pydantic 序列化排除，
`TraceRecorderSink` 只能通过显式 `to_trace_event()` 投影持久化。首版 sink 只有 no-op、trace 和 queue
三种实现及一个简单组合 sink，不引入 broker、订阅注册表或 mapper 框架。

`CompositeRunEventSink.publish()` 是 `sequence_no` 的唯一分配点。生产者发布 `sequence_no=None` 的
事件，组合 sink 在按 run 加锁的临界区内原子递增序号，再将同一个已编号事件依次交给 trace 与
queue sink。Runtime、ModelGateway 和 CapabilityGateway 不得各自维护计数器，也不新增 sequencer 服务。

Textual 不读取 LangGraph event、message、checkpoint 或 channel。共享 `_run_stage()` 包装器统一发布
节点生命周期，避免 Native/LangGraph 各实现一套。事件使用 `run_id + request_id + logical_call_id +
attempt + sequence_no` 关联；`CapabilityRequest` 同步补充 `run_id`，工具事件不得再缺失运行身份。

模型思考不来自 Runtime 或 LangGraph。OpenAI-compatible adapter 只解析 provider 响应中显式存在的
`message.reasoning_content`，归一化为项目 `ModelResult.reasoning_content` 可选字段；该字段设置
`exclude=True, repr=False`，任何 `model_dump()`、模型 `repr`、异常日志都不得包含原文。未返回、
`null` 或空字符串时保持 `None`；
非字符串值归类为 provider 响应格式错误。模型调用边界将裁剪脱敏后的 reasoning 直接放入
`RunProgressEvent.transient_payload`，持久化投影只记录 available、原始字符数和裁剪状态。
Agent、WorkflowState 和 Runtime 不保存、解析或依赖 reasoning 文本。

模型 started/finished/failed 与 reasoning 事件由组合根装配的 `ObservableModelGateway` 装饰器统一
发布。装饰器在收到完整 `ModelRequest` 后、调用底层 Gateway 前发布真实模型输入视图，完成后发布
输出、Usage 与瞬态 reasoning。Agent 只构造请求和消费结果，不依赖 `RunEventSink`；现有阶段中的
重复模型埋点迁移到装饰器。禁止用早于请求构造的 profile 配置事件冒充模型输入。

### 5.2 事件补充

`RunProgressEvent` 使用 Pydantic 判别联合，不使用任意字符串加无类型 dict。公共字段包括 run、request、
session、node、logical call、attempt、sequence 和时间；`kind` 至少覆盖：

```text
run_started | node_started | node_finished | node_failed
model_started | model_finished | model_failed
capability_started | capability_finished | capability_failed
run_cancelled | run_finished
```

每个 kind 对应独立 payload 类型；node/model/capability 的 started 与 finished/failed 不能互相替代，
`run_finished` 只作为 run 级终止屏障。`transient_payload` 也使用受控 Pydantic 类型，目前只允许
裁剪脱敏后的 Prompt/message、reasoning 和详细 JSON 视图。

在现有业务 trace 基础上补充：

- `node_started`：node、phase、attempt、脱敏输入摘要。
- `node_finished`：node、phase、attempt、耗时、`StatePatch` 摘要。
- `node_failed`：项目错误码、retryable、耗时和安全错误摘要。
- `run_finished`：唯一终止屏障，包含停止原因、聚合 Usage、总耗时和最终状态。
- `run_cancelled`：用户在运行中退出时记录取消；随后仍发布唯一
  `run_finished(status=cancelled, stop_reason=user_cancelled)`。

工作流协议同步增加 `RunStatus.CANCELLED` 与 `StopReason.USER_CANCELLED`。取消前尚未产生的 Usage 和
最终状态保持缺失，不用空对象伪造；终止事件仍携带已完成模型调用的已知 Usage 明细。

节点输入输出必须采用项目 Pydantic 类型序列化后的受控视图，不能把 LangGraph state、Command 或 provider 响应放入事件。

### 5.3 Textual 并发

- TUI 使用 Textual worker 执行 async `WorkflowRuntime.invoke()`。
- 项目事件通过同一 event loop 的无界 `asyncio.Queue` 推送，首版禁止丢事件。
- UI 更新必须在 Textual message loop 中完成。
- 单会话默认一次只运行一个请求；运行中禁止重复发送，但允许浏览历史轮次。
- 组合 sink 保证单 run 入队顺序严格递增。消费者对重复或旧序号幂等忽略；收到大于
  `last_sequence_no + 1` 的未来序号时立即将该 run 的本地展示置为 `event_sequence_gap` 失败并停止
  spinner，禁止静默跳过。消费者继续排空但不渲染该 run 的后续业务事件；只把 `run_finished` 当作
  队列清理确认，不允许它覆盖本地 gap 失败状态。测试中的 `1,3,2` 必须断言序号 3 触发失败、迟到
  的 2 不被应用、spinner 已停止且后续终止屏障只完成清理，不把乱序当正常路径。
- `run_finished` 必须在同一 run 的所有前序事件入队后发布；UI 消费到它才停止 spinner 和自动收起。
- 用户手动展开的节点不因完成事件被收起；失败强制展开优先于用户手动收起。
- `Ctrl+R` 保留原 `request_id`、创建新 `run_id`，符合“同一用户请求、多次运行尝试”语义。
- Runtime 外层统一 `try/except/finally`，是 `run_cancelled` 和唯一 `run_finished` 的唯一生产者。
  Textual 的 `Ctrl+C` 只取消 worker，并最多等待 2 秒消费终止屏障；超时显示本地退出错误但不伪造
  业务事件，随后回收 worker，禁止遗留永久 spinner 或后台任务。

## 6. 输入输出与脱敏

### 6.1 默认摘要

- 节点输入：phase、已确认案件事实、意图、证据计数和能力结果计数。
- 节点输出：目标 phase、被更新字段和 append/merge 数量。
- 模型输入：Prompt ID/version、profile、schema 摘要和裁剪后的消息。
- 模型思考：provider 显式返回并经裁剪脱敏后的 `reasoning_content`，默认折叠。
- 模型输出：结构化业务输出、finish reason、usage 和耗时。
- 工具输入输出：CapabilityGateway 治理后实际参数、结果、状态、fallback 和耗时。

### 6.2 安全规则

以下字段在摘要、原始 JSON 和错误信息中始终移除或替换为 `***`：

- API key、Authorization、Cookie 和代理凭据。
- `SecretStr` 内容、敏感键的嵌套值，以及已配置 secret 的精确值。
- provider 完整错误体中的潜在敏感字段。

敏感键递归匹配 dict/list 中的 api_key、authorization、cookie、token、password、proxy credential
及其大小写变体；URL query/header 同样处理。普通 PATH、HOME 等非敏感环境变量不做无差别删除。

长 Prompt、工具结果和文档正文按字符数与条目数裁剪，并标记原始长度。TraceRecorder 是业务事件
事实来源，但遵守最小必要保存原则，不承诺保存被裁剪的 Prompt、reasoning 或文档原文。

reasoning 内容按独立上限裁剪并执行与模型输出相同的敏感字段脱敏。首版只在当前 TUI 会话内展示
裁剪后的 reasoning，不把 reasoning 原文写入 AgentMessage、WorkflowState、TaskState、RunReport、
SessionState、业务 trace、badcase、eval 或 differential artifact；trace 只记录
`reasoning_available`、原始字符数和裁剪状态。新会话、`Ctrl+L` 和退出时释放内存中的 reasoning。

## 7. Usage 状态行

AI 消息完整输出后显示本轮所有模型调用的聚合数据：

```text
↑ 455 输入  ↓ 380 输出  Σ 835 tokens  ⚡ 104.3 tok/s  ◷ 6.1s
```

口径：

- `ModelUsage` 新增 `reported: bool`，明确区分 provider 报告的零值与未报告 usage。
- 输入、输出、cache 和 total token 对本轮所有成功返回且 `reported=True` 的 `ModelResult` 求和。
- 输出速度为总输出 token / 模型调用累计耗时；无输出、零耗时、fake 或任一成功 provider usage
  未报告时显示 `--`。
- 总耗时覆盖完整 Runtime，而非只计算模型调用。
- 多模型明细放在执行过程的模型节点中。
- 任一成功 provider 调用 `reported=False` 时，聚合 token 显示 `tokens unknown` 且速度显示 `--`；
  展开区仍展示其余已知调用，但不据此生成看似完整的合计。
- Fake 固定为 `reported=False, usage_source=fake`，只存在 fake 调用时显示 `fake · 0 tokens`，不触发
  provider unknown；失败且没有 ModelResult 的尝试不计 token，重试中每个成功 ModelResult 分别计入。
- provider 的 total 与 input/output/cache 不一致时保留 provider total，并在展开区标记 inconsistent，禁止自行改写。

## 8. 错误与空状态

- Provider、模型、工具、校验和安全错误使用项目错误码映射为用户可读消息。
- 失败节点自动展开；错误详情不得包含 secret 或完整敏感响应。
- 无政策证据时明确说明证据不足并给出补充方向。
- `other`、clarification、capability failure 和 safety blocked 均必须有可见消息。
- TUI 启动配置错误时显示全宽脱敏错误面板，只允许退出；首版不支持配置热重载。
- `chat` 在非 TTY 或 `TERM=dumb` 下以退出码 2 明确报错，不回退旧逐行模式。

## 9. Chat 命令与能力迁移

旧逐行 shell 交互循环不保留，但已有业务能力迁移为 TUI action/modal，并在输入框保留
轻量 slash command 候选面板：

| 旧命令 | TUI 行为 |
|---|---|
| `/help` | 输入 `/` 后候选；`F1` 打开帮助 |
| `/new` | 输入 `/` 后候选；`Ctrl+N` 新会话 |
| `/context` | 输入 `/` 后候选；`F2` 打开当前 session 上下文和已完成轮次摘要 |
| `/trace` | 输入 `/` 后候选；执行树常驻，`F3` 显示 trace 文件和关联 ID |
| `/badcase` | 输入 `/` 后候选；`F4` 打开反馈/badcase 表单 |
| `/feedback good|bad` | 输入 `/` 后候选；反馈按钮/快捷键打开确认或 badcase 表单 |
| `/exit` | 输入 `/` 后候选；退出 chat |

输入 `/` 后上下键只移动候选，`Tab` 将候选补全到输入框，`Enter` 提交当前输入，`Esc` 收起候选。
`Ctrl+N` 和 `/new` 重置 session 和 turn；`Ctrl+L` 只清空屏幕，不修改 session、turn 或持久化数据；
`F2`/`/context` 的历史摘要只存在当前 TUI 进程内，不改变 Runtime memory 协议；重试保留 request ID
并更换 run ID。现有会话复用、turn 递增、feedback、badcase 和命令面板语义必须迁移到 Pilot 测试。

## 10. 组件边界

建议新增或调整：

- `ananhu_agent/cli/tui/app.py`：Textual App、worker 和会话生命周期。
- `ananhu_agent/cli/tui/widgets/turn.py`：单轮用户/过程/AI/Usage 组合。
- `ananhu_agent/cli/tui/widgets/run_inspector.py`：节点、模型、工具树。
- `ananhu_agent/cli/tui/presentation.py`：事件到展示模型的纯转换、裁剪和脱敏。
- `ananhu_agent/ports/model_gateway.py`：增加序列化排除的 reasoning 与 `ModelUsage.reported`。
- `ananhu_agent/infrastructure/models/openai_compatible.py`：解析显式 `message.reasoning_content`。
- ModelGateway 组合根：新增最小 `ObservableModelGateway` 装饰器，集中发布模型生命周期和瞬态 reasoning。
- `ananhu_agent/ports/run_event_sink.py`：框架中立事件发布端口。
- `ananhu_agent/infrastructure/events/queue_sink.py`：Textual 队列适配器。
- Capability 协议：补充 `run_id`，保证工具事件可归属到唯一运行。
- Workflow contract：补充 cancelled 状态与 user-cancelled 停止原因。
- `ananhu_agent/cli/main.py`：`chat` 改为启动 Textual App。

Rich/Textual 类型只能存在于 `cli/tui` 展示层。domain、application、Agent、Tool、Prompt、Eval 和 Runtime 公共协议不得导入 Textual。

## 11. 测试策略

1. 事件时序：用 barrier Fake Runtime 注入 `1,2,2,3`、`1,3,2` 和两个交错 run，验证重复幂等、
   gap 显式失败、跨 run 关联、唯一终止屏障、无丢事件和禁止重复发送。
2. Textual Pilot：键盘/鼠标逐层独立折叠；兄弟状态互不影响；摘要/JSON 切换；新会话、清屏、重试、取消、帮助、上下文、反馈和 badcase。
3. 布局：固定 `80x24`，覆盖中文、长无空格字符串、Markdown 表格、四层树、深层 JSON 和运行中 resize；页面无水平滚动或重叠，JSON 区可局部滚动。
4. Contract：Native/LangGraph 每个节点 `started -> finished|failed` 唯一配对，`run_finished` 唯一且最后；payload 递归禁止 LangGraph/Textual/Rich 类型。
5. Presentation：节点、模型、工具输入输出摘要、非法/超长 JSON、裁剪和递归敏感字段脱敏。
6. Reasoning：存在、缺失、null、空串、非法类型、边界长度和超限；默认折叠，扫描 repr、traceback、
   日志和所有持久化 artifact 无原文。
7. Secret canary：测试运行时随机生成唯一值，放入 reasoning、Prompt、工具结果、header、URL、
   SecretStr 和 provider 错误体，扫描屏幕、错误、repr、traceback、日志、状态、报告、badcase、eval、
   pytest captured output 和 Git。
8. Usage 表驱动：单/多模型、cache、fake、缺失、混合、失败、重试、零输出、零耗时和 inconsistent
   total；混合未报告的精确期望为 `tokens unknown` 与速度 `--`。
9. `other`：两个 Runtime 下问候和非领域输入均返回确定性非空文案，且没有政策、测算和证据校验 capability 事件。
10. Error：参数化 model/tool/node/reducer/evidence/safety 和全部 StopReason，断言消息非空、失败路径展开且错误脱敏。
11. Terminal：真实 PTY smoke、非 TTY、`TERM=dumb`、resize 和不支持 Shift+Enter；每个子进程设置
   10 秒超时并断言回收，禁止 traceback、挂起或静默空白。
12. Regression：全量 pytest、`ask`、`eval`、`eval --runtime both`、`version` 在非 TTY 下执行，
   核对退出码、关键 stdout 和 metrics/differential/trace 产物，证明 TTY 门禁只作用于 `chat`。

下表是规格级分类。实施计划必须将其展开为真实测试函数 ID、完整 `uv run pytest ...` 命令和精确
断言；只为布局、事件序列和 canary 扫描保留必要 artifact，不为每个单元测试新增长期证据文件。

| 验收域 | 测试 ID | 命令/方式 | 精确证据 |
|---|---|---|---|
| 实时事件 | `EVT-*` | runtime event contract pytest | lifecycle 序列 JSON；唯一终止、sequence 单调、无跨 run 污染 |
| 折叠交互 | `TUI-*` | Textual Pilot | 关键屏幕快照；节点/工具输入输出独立展开矩阵 |
| 80 列布局 | `LAY-*` | Pilot `80x24` + resize | widget region 断言与前后快照；页面无水平滚动/重叠 |
| Reasoning | `REA-*` | adapter/runtime pytest | provider 方言矩阵；所有持久化 artifact 无 reasoning 原文 |
| Secret | `SEC-*` | canary pytest + `rg` 审计 | 屏幕、错误、JSONL/JSON、测试输出和 Git 零命中 |
| Usage | `USE-*` | 表驱动 pytest | 每个输入组合对应精确状态行和逐模型明细 |
| `other`/错误 | `FLOW-*` | 双 Runtime contract | 非空用户消息、无禁止 capability 事件、失败路径展开 |
| 终端/回归 | `PTY-*`/`REG-*` | PTY smoke + CLI/pytest/eval | 退出码、stdout、metrics、differential 和 trace 审查 |

## 12. 验收标准

- `uv run ananhu-agent chat` 直接进入 Textual TUI。
- 用户可用键盘或鼠标逐层展开每个节点、模型和工具的输入输出。
- provider 显式返回 reasoning 时可展开查看裁剪脱敏后的内容；无 reasoning 时不显示空节点。
- 执行树在 Runtime 运行期间实时更新，完成后自动收起。
- AI 消息支持 Markdown，消息末尾展示本轮聚合 Usage。
- `你好` 和其他 `other` 输入不会产生空白回复。
- 节点失败自动展开并显示脱敏错误。
- Pilot `80x24` 下顶部、会话区、输入区和底栏不重叠且无页面级水平滚动；四层树标签/状态可见，JSON 只在局部区域滚动。
- Native/LangGraph 不向 TUI 泄漏框架类型，业务 trace 仍是共同事实源。
- API key canary 不出现在屏幕、错误、状态、报告、trace、badcase、eval、测试输出或 Git 中。
- v0.7 架构正文、入口、02/04/05 分册和 changelog 在实现前完成版本化同步。

## 13. 实施顺序门禁

1. 发布 v0.7 架构文档并同步入口、运行时、模型、观测分册和 changelog。
2. 实现 `RunProgressEvent`、身份/sequence/终止协议及双 Runtime contract。
3. 实现 reasoning 瞬态安全路径、Usage reported 语义和 canary 测试。
4. 实现 `other`、全部停止原因可见消息和取消语义。
5. 实现 Textual 单栏 TUI及旧 chat 能力迁移。
6. 执行 Pilot、真实 PTY、全量回归和差分验收。

后续实施计划必须按此依赖顺序拆分，每项可以独立验证，不能先搭 widgets 再补事件协议。

## 14. 已知限制

- 首版不支持模型 token 级流式输出。
- 首版只兼容 OpenAI-compatible `message.reasoning_content`；其他 provider 方言后续按适配器扩展。
- Textual TUI 需要支持 ANSI 和交互输入的终端；CI 使用 Pilot/headless 测试。
- 超大 JSON 只展示裁剪视图；其他允许持久化的业务证据通过受控 trace 查询。
- 首版不提供剪贴板复制、保存片段或配置热重载。
