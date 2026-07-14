# Agent Kernel 第六章学习实施路线确认

> 日期：2026-07-12
>
> 状态：已由用户确认并写入 DEV_SPEC v0.24
>
> 基线：DEV_SPEC v0.23

## 1. 章节职责

第六章回答：

> 从实现准入到首个 Kernel 架构版本，应该按什么顺序学习和实现，每一步交付什么，又如何证明完成？

目录本身必须能够作为施工地图，不应只显示阶段名称而把任务隐藏在表格中。

## 2. 方案选择

采用参考文档的“阶段总览 + 进度跟踪 + 详细任务 + 总体进度 + 里程碑”表达方式，并按 Agent Kernel 学习目标重新设计任务。

不照搬参考项目的具体业务模块、文件路径、Factory 数量或技术实现。

## 3. 阶段路线

```text
A 规格与实现准入
B Model MVP
C Agent MVP
D Tool Call 闭环
E Memory 跨运行上下文
F Runtime 与 Execution
G Workflow 控制语义
H Kernel 累计验收与发布
```

共 47 个任务。

## 4. 任务模板

每个任务必须回答：

| 字段 | 问题 |
|---|---|
| 学习问题 | 该任务帮助理解什么 Agent 机制 |
| 前置依赖 | 哪些任务和设计必须先完成 |
| 交付 | 产生什么协议、实现、测试或证据 |
| 验收 | 什么可观察结果证明任务完成 |
| 关联 | 对应哪些 K、RD 或门禁 |

文件路径、类名、方法签名和具体测试节点由模块确认后的实施计划补充。

## 5. 核心调整

- 原 A1-A10 是文档修订历史，不再作为实现排期。
- Model、Agent、Tool、Memory、Runtime、Workflow 按真实链路逐步接入。
- Execution 的 Streaming、Cancellation、Hooks、Guardrails 和 Retry 分别拆成任务。
- 每个阶段都以真实 RD 和历史 RD 累计回归作为出口。
- Application、Interface 和业务 Evals 不进入第一阶段 Kernel 排期。
- H 阶段只负责累计验收、架构发布和学习成果收口。

## 6. 门禁

```text
A 实现准入
  -> B RD-001
  -> C RD-002
  -> D RD-003
  -> E RD-004
  -> F RD-005、RD-008、RD-009、RD-010、RD-012
  -> G RD-006、RD-007、RD-011
  -> H 全部 K / RD
```

每个箭头都包含历史 RD 回归。`BLOCKED` 和 `NOT RUN` 不算通过。

## 7. 边界

本次确认不决定：

- 物理目录。
- Python 类型库。
- 具体 Provider SDK。
- 具体文件和测试节点。

本次确认不授权创建 Kernel 代码目录。代码实现必须等待 A2、A3 和对应模块设计确认。
