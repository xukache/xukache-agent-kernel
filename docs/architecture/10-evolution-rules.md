# 10. 架构演进与变更监控

## 变更同步规则

- 修改运行时所有权、阶段、State、StatePatch、reducer、StopReason 或 checkpoint 时，更新 `02-agent-runtime.md`。
- 修改 Prompt、Context、Memory、CaseFact 或裁剪规则时，更新 `03-prompt-context.md`。
- 修改 Capability、Model、Knowledge、Evidence、幂等或重试时，更新 `04-tools-models.md`。
- 修改 Trace、Usage、Badcase、Eval 或隐私字段时，更新 `05-data-observability.md`。
- 架构级事实变化必须更新 `99-changelog.md`。
- 外部接口变化必须先更新 `docs/api-contracts.md`。

## 框架隔离监控

以下情况视为架构违规，必须在同一变更中修正：

- domain/application/Agent/Tool/Eval 公共协议导入 LangGraph、LangChain、Agno 或模型供应商类型。
- LangGraph state 被当作案件事实或数据库 schema。
- Graph node 内包含本应属于 application/domain 的业务规则。
- Native Runtime 被完整包装进一个图节点，形成双状态机。
- LangGraph/LangSmith trace 替代项目 TraceEvent。
- 框架 checkpointer 被当作唯一业务状态库。

可以通过静态导入测试或 `rg` 检查这些边界。

## Agent 与工作流监控

- 新增 Agent 前记录拆分依据和单 Agent baseline。
- Agent 数量变化不应自动导致图节点数量变化。
- 新增并行分支前证明无前置依赖、共享事实版本和确定性合并规则。
- 新增循环前定义步骤上限、重试上限、停止原因和成本预算。
- 新增人工中断/恢复前定义 checkpoint 兼容和幂等策略。

## 状态与数据监控

- Case、Session、Run、Checkpoint、Trace 的职责和生命周期不能合并。
- 新持久化字段必须有 schema version、来源、隐私等级和保留策略。
- jurisdiction、政策版本、关键事实或公式变化必须触发依赖数据失效。
- trace/badcase 不得默认保存不必要的完整敏感原文。

## 文档一致性监控

每次架构或计划变更扫描：

- “尚未初始化”“尚未实现”等阶段描述是否仍真实。
- Agno、LangGraph、Native Runtime 的当前与目标边界是否一致。
- 当前四 Agent 是否被误写成永久强制架构。
- fake/fixture 测试是否被误写成真实业务验收。
- 当前无 API 是否被误写成永久不支持外部接口。
- 已作废计划项是否仍被列为待执行路线。

## 禁止项

- 不为了目录或名词现代化进行无行为收益的大规模重写。
- 不在没有真实需求和测试前建设通用 DAG、复杂工作流平台或多套 checkpoint。
- 不提前虚构 API、流式事件或多模态实现。
- 不让实施计划覆盖当前架构事实源。
- 不删除已发布的审计历史和版本快照；实现代码中未使用的旧架构、兼容入口和废弃逻辑应在对应变更中删除，并在 changelog 标注迁移影响。
