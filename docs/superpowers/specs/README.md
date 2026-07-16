# 设计确认记录

本目录保存 Agent Kernel 的模块、章节和阶段设计确认记录。当前完整规格版本为
`DEV_SPEC v0.26`。`DEV_SPEC.md` 维护当前完整规格，本目录负责保留确认过程、设计理由
和实现准入证据，不与完整规格形成平行事实源。

## 当前确认状态

| 主题 | 状态 | 记录 |
|---|---|---|
| Kernel 总体边界、Execution、六个核心原语、支撑协议、Application、Interface | 已确认 | [`2026-07-12-agent-kernel-rebuild-design.md`](2026-07-12-agent-kernel-rebuild-design.md) |
| 学习定位与第一章 | 已确认 | [`2026-07-12-agent-kernel-learning-positioning-design.md`](2026-07-12-agent-kernel-learning-positioning-design.md) |
| 核心特点与第二章 | 已确认 | [`2026-07-12-agent-kernel-core-features-design.md`](2026-07-12-agent-kernel-core-features-design.md) |
| 技术决策与第三章 | 已确认 | [`2026-07-12-agent-kernel-technology-decisions-design.md`](2026-07-12-agent-kernel-technology-decisions-design.md) |
| 测试验收与第四章 | 已确认 | [`2026-07-12-agent-kernel-testing-acceptance-design.md`](2026-07-12-agent-kernel-testing-acceptance-design.md) |
| 系统架构语义与第五章 | 已确认 | [`2026-07-12-agent-kernel-system-architecture-design.md`](2026-07-12-agent-kernel-system-architecture-design.md) |
| 系统架构表达与第五章 | 已确认 | [`2026-07-12-agent-kernel-system-architecture-presentation-design.md`](2026-07-12-agent-kernel-system-architecture-presentation-design.md) |
| 学习实施路线与第六章 | 已确认 | [`2026-07-12-agent-kernel-learning-roadmap-design.md`](2026-07-12-agent-kernel-learning-roadmap-design.md) |
| 完整 Agent 系统演进路线与第七章 | 已确认 | [`2026-07-13-agent-system-evolution-roadmap-design.md`](2026-07-13-agent-system-evolution-roadmap-design.md) |
| Memory scope、会话隔离与跨会话共享 | 已确认，待 E1-E6 实现 | [`2026-07-15-agent-kernel-memory-scope-sharing-design.md`](2026-07-15-agent-kernel-memory-scope-sharing-design.md) |
| A1 开发规格确认与实现准入 | 已完成 | [`2026-07-13-agent-kernel-implementation-admission-a1.md`](2026-07-13-agent-kernel-implementation-admission-a1.md) |
| A2 公共类型表达策略 | 已完成 | [`2026-07-13-agent-kernel-public-type-strategy-design.md`](2026-07-13-agent-kernel-public-type-strategy-design.md) |
| A3 物理目录与公开导入路径 | 已完成 | [`2026-07-13-agent-kernel-physical-layout-import-paths-a3.md`](2026-07-13-agent-kernel-physical-layout-import-paths-a3.md) |
| A4 uv、pytest 与 Architecture Test 基座 | 已完成 | [`2026-07-14-agent-kernel-engineering-test-foundation-a4.md`](2026-07-14-agent-kernel-engineering-test-foundation-a4.md) |
| A5 真实对话证据基座 | 已完成 | [`2026-07-14-agent-kernel-real-dialogue-evidence-foundation-a5.md`](2026-07-14-agent-kernel-real-dialogue-evidence-foundation-a5.md) |
| B1 ModelRequest 与 ModelResponse | 已完成 | [`2026-07-14-agent-kernel-model-request-response-b1.md`](2026-07-14-agent-kernel-model-request-response-b1.md) |
| B2 Model Contract 与错误语义 | 已完成 | [`2026-07-14-agent-kernel-model-contract-errors-b2.md`](2026-07-14-agent-kernel-model-contract-errors-b2.md) |
| B3 Volcengine Ark Model Adapter | 已完成 | [`2026-07-14-agent-kernel-volcengine-adapter-b3.md`](2026-07-14-agent-kernel-volcengine-adapter-b3.md) |
| B4 结构化输出转换 | 已完成 | [`2026-07-14-agent-kernel-structured-output-b4.md`](2026-07-14-agent-kernel-structured-output-b4.md) |
| B5 Provider Streaming 转换 | 已完成 | [`2026-07-14-agent-kernel-provider-streaming-b5.md`](2026-07-14-agent-kernel-provider-streaming-b5.md) |
| B6 RD-001 真实模型验收 | 已完成 | [`2026-07-14-agent-kernel-real-model-acceptance-b6.md`](2026-07-14-agent-kernel-real-model-acceptance-b6.md) |
| C1 Agent 公共调用边界 | 已完成 | [`2026-07-16-agent-kernel-agent-contract-c1.md`](2026-07-16-agent-kernel-agent-contract-c1.md) |
| C2 Instructions 与 ModelRequest 组装 | 已完成 | [`2026-07-16-agent-kernel-model-request-builder-c2.md`](2026-07-16-agent-kernel-model-request-builder-c2.md) |
| C3 最小 Agent 推理循环 | 已完成 | [`2026-07-16-agent-kernel-agent-loop-c3.md`](2026-07-16-agent-kernel-agent-loop-c3.md) |

## 模块确认记录模板

后续新增或修改模块必须按以下结构记录：

| 字段 | 必须回答的问题 |
|---|---|
| 目标 | 这个模块为用户或系统提供什么能力？ |
| 输入 | 接收哪些结构化数据和运行上下文？ |
| 输出 | 返回什么结果、事件和 usage？ |
| 核心职责 | 模块自己做什么？ |
| 非职责 | 明确不做什么，防止边界漂移 |
| 依赖 | 依赖哪些 Core Protocol 或 Adapter？ |
| 生命周期 | 如何开始、暂停、恢复、取消和结束？ |
| 错误 | 错误类别、是否可重试、是否终止 |
| 可替换点 | 替换实现时公共协议是否保持不变？ |
| 测试 | 对应哪些 Unit、Contract、Integration 或 E2E？ |
| 证据 | 用什么文件、事件、日志或测试结果证明完成？ |

## 实现准入门禁

模块只有同时满足以下条件，才允许创建对应代码目录：

1. 模块边界已确认。
2. 最小输入、输出和错误已写入 `DEV_SPEC.md`。
3. 至少关联一个验收 ID。
4. 已明确是否需要真实 Model Integration。
5. 已说明对其他文档和版本的影响。
6. 已定义一个真实对话输入、该模块必须承担的职能、预期输出或事件，以及累计回归范围。

Python 类型表达已在 A2 完成确认；物理目录和公开导入路径已在 A3 完成确认；
A4 已建立并确认工程和测试基座；A5 已建立真实对话场景注册和证据写入基座；
B6 已通过真实 Volcengine Provider 完成 RD-001，Model MVP 已完成。
C1 已确认并完成 AgentDefinition、AgentInput、AgentResult、状态、停止原因和错误
边界；RD-002 仍由 C5 负责。
