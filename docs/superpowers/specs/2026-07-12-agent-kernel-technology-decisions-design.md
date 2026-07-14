# Agent Kernel 第三章技术决策设计确认

> 日期：2026-07-12
>
> 状态：已由用户确认
>
> 对应开发规格：DEV_SPEC v0.20

## 1. 章节职责

第三章只回答：

> 为了学习并实现 Agent Kernel，哪些核心机制需要自行实现，哪些通用基础设施应当复用，第一阶段为什么采用当前技术组合？

第三章不作为完整公共字段、模块执行流程、测试场景或实施任务的事实源。

## 2. 方案选择

已确认采用学习导向的技术决策章：

- 核心机制亲手实现。
- 通用基础设施复用成熟工具。
- 每项选择说明理由、限制和替换边界。
- 尚未确认的具体 SDK 和库明确延后。
- 详细协议和执行规则统一归入第五章。

未采用完整技术方案型章节，避免与第五章重复；未采用单纯技术栈清单，避免只列技术名称而缺少决策理由。

## 3. 已确认结构

```text
3.1 技术选型目标与判断标准
3.2 自研与复用边界
3.3 Python 工程与异步执行基线
3.4 公共协议与结构化数据策略
3.5 第一阶段 Adapter 选择
3.6 配置、凭证与 Provider 隔离
3.7 可观测性与测试工具策略
3.8 第一条纵向切片技术基线
3.9 延后决定的技术选项
```

## 4. 自研边界

必须自行设计和实现：

```text
六个 Core Protocol
Agent 执行循环
Tool Call 循环
Memory 使用语义
Workflow 状态推进
Runtime 生命周期
Execution 支撑语义
Adapter 边界
```

成熟 Agent 框架不能替代上述核心行为，也不能成为 Kernel 公共协议来源。

## 5. 复用边界

应当复用成熟能力：

```text
Provider 网络通信
Schema 校验与序列化
测试执行器
uv 环境和依赖管理
Python 标准异步基础
数据库与外部存储客户端
后续 Interface 框架
```

具体 Provider SDK、Schema 库、持久化客户端和 Interface 框架仍需在对应模块确认时选择。

## 6. 第一阶段技术组合

| 能力 | 当前选择 |
|---|---|
| Python | 3.11 |
| 环境与依赖 | `uv` |
| 测试 | `pytest` |
| Model | 一个真实 Provider Adapter |
| Memory | In-memory Adapter |
| Tool | 无副作用结构化 Tool |
| Runtime | 单进程本地 Runtime |
| Observability | In-memory Events Collector |
| Interface | 程序化测试入口 |

具体模型标识属于运行配置，不属于 Kernel 架构。

## 7. 信息迁移确认

以下已确认内容不再由第三章重复维护：

| 内容 | 事实源 |
|---|---|
| `ModelRequest`、`ModelResponse` | 第五章 Model 模块 |
| `WorkflowState` | 第五章 Workflow 模块 |
| Context、Retry、Cancellation、Streaming、Hooks、Guardrails | 第五章 Execution 执行流程 |
| `RD-*` 场景 | 第四章 |
| 实施顺序 | 第六章 |

## 8. 边界

本次确认不改变：

- 六个核心原语及运行链路。
- 真实 Provider 必须参与主要验收。
- 不允许模拟模型或静默 fallback。
- 业务 Application 延后。
- 当前不得创建代码目录。

本次确认只完成第三章设计，不代表第四章及后续章节已经通过本轮逐章审查。
