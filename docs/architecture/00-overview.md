# 架构总览

Agent Kernel 用六个核心原语建立最小心智模型：

```text
Agent
Workflow
Tool
Memory
Model
Runtime
```

Execution 中的 Context、Hooks、Guardrails、Retry、Cancellation 和 Streaming 是支撑协议，不新增核心原语。

## 逻辑分层

```text
External Callers
  -> Interface
  -> Application / Composition Root
  -> Runtime
      -> Agent 或 Workflow
          -> Model / Tool / Memory Protocol
  -> Adapter
  -> External Systems

Runtime / Core
  -> Events / Results / Errors
  -> Observability / Test Evidence
```

| 层 | 职责 |
|---|---|
| Interface | 输入转换、事件转发、结果序列化和错误映射 |
| Application / Composition Root | 创建 Definition、选择 Adapter、注入配置和组装运行对象 |
| Kernel | 执行 Agent 或 Workflow，维护公共语义和结构化证据 |
| Adapter | 把稳定 Protocol 转换为 Provider、Backend、Store 或 Runtime 的具体调用 |
| External Systems | 模型服务、工具后端、存储和外部运行资源 |
| Observability | 消费 Events、Result、受控日志和测试证据，不控制业务运行 |

## 核心运行关系

- Runtime 拥有一次 Run 的生命周期和唯一终态。
- Agent 拥有 Model、Tool、Memory 的推理闭环。
- Workflow 拥有步骤调度、流程位置和 WorkflowState。
- Model 提供 Provider Neutral 的生成能力，不执行 Tool。
- Tool 把结构化意图转换为一次受治理的外部动作。
- Memory 是按 scope 分区的统一能力，负责存储、检索和隔离，不决定记忆内容。
- Application 提供会话、用户和可选项目身份以及 Memory Policy；Agent 选择读取
  scope、写入目标和 MemoryItem 来源。
- 会话级、用户级和项目 / 共享级 scope 默认隔离，跨会话共享必须显式读取用户级或
  项目级 scope。

## 当前阶段边界

- 已冻结逻辑架构和语义级公共契约。
- A3 已冻结 `src/agent_kernel` 物理目录基线和公开导入路径规则；当前已由 B1-B6
  建立 Model 公共协议、Volcengine Adapter、结构化输出、Streaming 和 RD-001
  真实验收。
- Agent、Tool、Memory、Runtime 和 Workflow 尚未创建实现目录。
- 第一阶段只建立单进程、单真实 Model Provider、In-memory Memory 和无副作用 Tool 的纵向切片。
- CLI、HTTP、MCP、业务 Application 和 Multi-Agent 属于后续确认范围。
- 当前完整架构版本为
  [`v0.1-memory-scope-sharing`](versions/v0.1-memory-scope-sharing.md)。

完整架构图与模块定义以 `DEV_SPEC.md` 第 5 章为准。
