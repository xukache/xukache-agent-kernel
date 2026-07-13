# 后端开发规范

本文档约束未来 Agent Kernel 的 Python 实现。当前物理目录和公开导入路径尚未由 A3 确认，因此这里只规定逻辑边界和工程原则。

## 工程基线

- Python 固定为 3.11，以 `.python-version` 为准。
- 建立 Python 工程后统一使用 `uv` 管理环境、依赖、测试和运行。
- 不从 `mvp`、`main` 或旧项目恢复 `pyproject.toml`、`uv.lock`、代码和测试。
- A3 确认前不得创建 Kernel 代码目录或提前声明包路径。
- 依赖版本和命令在 A4 建立工程基座时确认，本文档不虚构未落地命令。

## 依赖方向

```text
Interface -> Application / Composition Root -> Kernel Contracts
Adapter   -> Kernel Contracts
Kernel    -X-> Interface / Application / Provider SDK / 具体存储
```

- `Agent`、`Workflow`、`Tool`、`Memory`、`Model`、`Runtime` 是唯一核心原语。
- Execution 是支撑协议集合，不是第七个核心原语。
- Application 负责组装 Definition、Adapter 和配置，不能反向进入 Kernel。
- 第三方 SDK、数据库客户端和外部运行框架只能存在于 Adapter 或 Interface 边界。
- Core 不导入具体 Adapter；Adapter 通过实现 Kernel Protocol 接入。

## 类型选择

| 场景 | 默认工具 | 规则 |
|---|---|---|
| 可替换行为契约 | `typing.Protocol` | 描述对象能做什么，不提供共享状态 |
| 只读装配对象 | frozen `dataclass` | `frozen=True, slots=True, kw_only=True, eq=False` |
| 跨边界结构化数据 | Pydantic v2 Schema | `frozen=True, extra="forbid", strict=True` |
| 运行时失败传播 | `KernelError` | 在明确模块边界捕获和映射 |
| 公开失败证据 | `ErrorInfo` | 可 JSON 序列化、脱敏、Provider Neutral |
| 稳定状态和原因 | `str Enum` | 不依赖 Provider 私有枚举 |
| 共享实现骨架 | ABC | 不是默认公共契约，仅在真实共享实现出现后内部使用 |

不得使用 `Any`、`object` 或无类型 `dict` 绕过公共契约。开放 JSON 只用于真正开放的 metadata、details 或业务 payload，并在 Schema 边界执行防御性复制和规范化。

## 异步与执行边界

- Model、Tool Backend、Memory Store 和未来远程 Runtime 等 I/O 能力使用异步契约。
- 同步 CPU 工作不得长期阻塞事件循环；具体执行策略由对应模块任务确认。
- `RunContext` 传递 deadline、取消和运行元数据，不替代 Memory 或 WorkflowState。
- 取消必须从 Runtime 向下游传播；取消或失败后不得再产生 completed 终态。
- Retry 只用于满足错误可重试、操作幂等、策略允许、次数未耗尽、deadline 未到且尚未取消的调用。

## 数据与状态

- Definition、Input、State、Event 和 Result 互不替代。
- Input 创建后不可回填运行数据。
- State 每次推进创建新实例，并通过 JSON 往返保持语义等价。
- Event 只追加，同一 run 内按 sequence 排序，每个 run 只能有一个 Terminal Event。
- Result 使用模块专属状态和校验器约束 output、error、state 的合法组合。
- Memory 只负责按 scope 存储和检索；WorkflowState 不进入 Memory。
- `resume_token` 属于 Runtime 恢复授权，不进入 WorkflowState。

## 错误与敏感数据

- Provider 或 Backend Exception 在 Adapter 边界映射为 `KernelError`，并用异常链保留内部 cause。
- 合法运行前的 Definition 或 Input 无效，直接抛出 `ValueError` 或 Pydantic ValidationError。
- 合法运行中的失败才转换为 failed Result、failure Event 和 `ErrorInfo`。
- Provider 原始错误码不能直接成为 Kernel 公共错误码。
- 凭证、traceback、SDK 对象、完整敏感 Prompt、原始响应和未脱敏用户数据不得进入 Result、Event、State 或 ErrorInfo。
- 完整诊断只进入受控日志或内部异常链。

## 注释与可读性

- 关键协议、所有权转换、错误映射和不明显的不变量使用中文注释说明职责与边界。
- 注释解释“为什么”和“不能做什么”，不复述代码。
- 公共名称保持 Provider Neutral，不把第一阶段 Adapter 名称写入 Core API。

## 测试与验证

变更的测试范围随边界扩大：

| 测试 | 证明内容 |
|---|---|
| Unit Test | 单个规则、校验器和确定性行为 |
| Contract Test | 不同实现遵守同一个 Protocol |
| Integration Test | 多模块数据流、失败和取消传播 |
| Architecture Test | 导入方向、Provider 类型隔离和公开 API |
| RD 真实对话验收 | 真实 Provider 下的用户可观察能力 |

提交前必须：

1. 运行与变更匹配的格式、静态检查和测试。
2. 模块出口任务累计运行当前 RD 和此前全部 RD。
3. 检查文档、任务状态和测试证据一致。
4. 未运行的验证明确标记，不能声称通过。

具体工具命令由 A4 确认后补充。
