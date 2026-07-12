# 从 Agent Kernel 到完整 Agent 系统的演进路线设计

> 日期：2026-07-13
>
> 状态：已由用户逐节确认并写入 `DEV_SPEC v0.25`
>
> 基线：`DEV_SPEC v0.24`

## 1. 设计目标

将原第七章从重复第五章的“模块扩展手册”，重构为 Kernel 完成后的系统演进路线，回答：

- Agent Kernel 与完整业务 Agent 系统有什么区别。
- Kernel 完成后为什么先建设 Agent Harness。
- 如何通过首个垂直业务 Application 验证 Kernel。
- 什么情况下才有必要从单 Agent 演进为 Multi-Agent。
- 如何用运行工件、Benchmark 和业务指标证明系统能力。

## 2. 参考材料及使用边界

本次设计对照了三类本地材料：

| 材料 | 主要用途 | 不直接迁移的内容 |
|---|---|---|
| `pico/pico.md` | Agent Harness 的控制面、状态面、证据面 | 未经本项目独立运行验证的指标和实现声明 |
| 饮食推荐 Agent | 垂直业务中的意图、槽位、路由、Fallback、Trace 和评估闭环 | 餐食业务模型、Java 实现和业务状态 |
| 面试官认可的多 Agent 项目 | 判断业务闭环和 Multi-Agent 必要性的评价标准 | “工业级”等缺少独立证据的包装性结论 |

参考材料只提供设计启发，不成为当前 Kernel 的代码、协议或实现来源。

## 3. 最终章节结构

```text
7.1 当前 Kernel 的能力边界
7.2 第一阶段：演进为可复盘的 Agent Harness
7.3 第二阶段：构建首个垂直业务 Application
7.4 第三阶段：用基线实验决定是否引入 Multi-Agent
7.5 完整 Agent 系统的证据闭环
7.6 暂不引入的复杂能力
```

整体演进顺序：

```text
Agent Kernel
  -> Agent Harness
  -> 垂直业务 Application
  -> 单 Agent 基线
  -> 有证据支撑的 Multi-Agent
  -> 必要时再评估平台化能力
```

## 4. 核心决策

### 4.1 Kernel 不是完整业务 Agent 产品

第一阶段继续只实现六个核心原语及其运行支撑能力。业务意图、槽位、规则、数据、RAG、反馈和业务指标不进入 Kernel。

### 4.2 Harness 不新增核心原语

Agent Harness 在 Runtime、Memory、Events 和 Adapter 之上补齐：

- 控制面：主循环、上下文预算和 Tool 治理。
- 状态面：Session、WorkflowState、Durable Memory 和 Checkpoint 分离。
- 证据面：`task_state.json`、`trace.jsonl`、`report.json` 和 Benchmark。

### 4.3 首个 Application 必须形成真实小闭环

Application 必须有明确用户、业务边界、事实来源、风险边界和成功指标，并形成：

```text
真实运行
  -> Trace
  -> Bad Case
  -> 人工标注
  -> 离线评估
  -> 修改
  -> 回归
```

### 4.4 Multi-Agent 必须晚于单 Agent 基线

只有独立目标、Instructions、Tool、上下文、输出和评估边界成立，并且同一评测集证明质量收益超过路由、通信、聚合、延迟和成本时，才允许正式引入 Multi-Agent。

### 4.5 所有效果声明必须可追溯

“生产可用”“工业级”“显著提升”等结论必须能够追溯到固定任务集、运行配置、版本、运行工件、失败样本和对照基线。

## 5. 文档职责调整

`DEV_SPEC.md` 最终止于第七章。原第 8-10 章迁移如下：

| 原内容 | 新归属 |
|---|---|
| 模块确认摘要 | `docs/superpowers/specs/` 下的既有设计记录和索引 |
| 模块确认模板、实现准入门禁 | `docs/superpowers/specs/README.md` |
| 开发规格维护与版本化 | `docs/dev-spec/README.md` |
| 文档索引、使用规则和阅读顺序 | 根 `README.md` |

这次调整只改变文档组织和未来路线表达，不改变六个核心原语、依赖方向、K/RD 验收语义或第一阶段实现范围。

## 6. 已知限制

- 首个垂直业务 Application 尚未选择。
- Agent Harness、运行工件和 Benchmark 仍属于 Kernel 完成后的路线，不进入当前 47 个任务。
- Multi-Agent 拆分方式必须等业务基线和运行数据出现后再设计。
- Python 类型表达、物理目录和首个 Provider SDK 仍待阶段 A 确认。
