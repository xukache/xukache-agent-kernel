# Agent Kernel 重构设计记录

> 状态：模块 1 已确认；整体设计仍按模块逐项确认。
>
> 分支：`mvp-agent-kernel-rebuild-task-36`
>
> 基线：`mvp` / v0.9

## 目标

重建一个简洁、通用、可组合的 Agent Kernel。第一阶段只稳定通用内核，不迁移现有工伤业务逻辑，也不保留旧业务协议兼容层。

## 已确认原则

1. 通用内核与业务应用完全分离。
2. 核心只保留少量稳定原语，不为每个阶段、能力或状态再创造一套平行名词。
3. Agent、Workflow、Tool、Memory、Model、Runtime 是第一阶段的核心原语。
4. 工伤认定、政策检索、待遇测算、jurisdiction、Evidence 等全部属于后续业务层。
5. 旧 `AgentContext`、`CapabilityCall`、`CapabilityGateway`、`StageService` 等概念不得原样迁移为新的核心抽象。
6. LangGraph 只能作为 Runtime Adapter，不能进入核心协议。

## 核心原语

| 原语 | 唯一职责 |
|---|---|
| `Agent` | 使用 Model、Instructions、Tools 和 Memory 完成一次智能任务 |
| `Workflow` | 组合 Agent、Tool 和函数步骤，负责顺序、分支、并行、重试和暂停恢复 |
| `Tool` | 对外部能力提供结构化输入、结构化输出和受治理执行 |
| `Memory` | 读取和写入可持久化上下文，不负责业务路由 |
| `Model` | 提供模型生成能力，不负责业务规则和状态持久化 |
| `Runtime` | 执行 Agent 或 Workflow 生命周期，不负责业务语义 |

## 依赖关系

```text
Runtime
  -> Workflow
      -> Agent
          -> Model
          -> Tool
          -> Memory
      -> Tool
      -> Memory
```

跨模块事件、错误和运行上下文属于内核基础协议，但不单独扩展为新的业务对象体系。

## 目标目录

```text
ananhu_agent/
  core/
    agent/
    workflow/
    tool/
    memory/
    model/
    context/
    events/
    errors/
  adapters/
    runtime/
    model/
    memory/
    observability/
  applications/
  interfaces/
```

`applications/` 第一阶段保持为空，不提前放入工伤领域模块。

## 核心禁止项

`core/` 不得依赖：

- 工伤业务词汇。
- 政策、赔偿、地区和 Evidence 类型。
- LangGraph、Provider SDK、CLI 或 Textual。
- 当前项目的 `schemas.py` 聚合协议。
- 具体 JSONL、HTTP 或模型供应商实现。

## 模块 1 验收标准

- 可以只阅读 `core/` 解释 Agent Kernel，不需要了解工伤业务。
- 核心原语之间只有明确依赖，不出现 AgentContext、CapabilityCall、StageService 等平行核心概念。
- 后续业务应用只能通过组合 Agent、Workflow、Tool、Memory 和 Model 接入。
- Runtime Adapter 可以替换，不改变核心原语的公共协议。
