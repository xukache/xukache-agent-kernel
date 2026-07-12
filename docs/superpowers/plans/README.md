# 实施计划索引

本目录只保留当前仍可执行的计划；已经完成或被新架构事实源替代的计划统一放入
`archive/`，不在本目录根路径保留副本或指针。

## 当前有效计划

| 状态 | 计划 | 说明 |
|---|---|---|
| 暂无 | - | 当前计划已完成；后续开发需创建新的版本化计划 |

计划中的任务只有在对应提交已经合并到 `mvp` 后才标记为 `[x]`。未完成任务不得归档。

## 已完成归档

| 状态 | 计划 | 结果 |
|---|---|---|
| 已完成，只读 | [`2026-07-09-cli-mvp-agent-harness.md`](archive/2026-07-09-cli-mvp-agent-harness.md) | CLI MVP Agent Harness 已合并 |
| 已完成，只读 | [`2026-07-10-textual-chat-tui.md`](archive/2026-07-10-textual-chat-tui.md) | Textual Chat TUI 已验收并合并 |
| 已完成，只读 | [`2026-07-11-knowledge-gateway-policy-baseline.md`](archive/2026-07-11-knowledge-gateway-policy-baseline.md) | KnowledgeGateway 与政策基线已合并 |
| 已完成，只读 | [`2026-07-11-direct-knowledge-capability-v0.9.md`](archive/2026-07-11-direct-knowledge-capability-v0.9.md) | v0.9 直接能力改造已合并 |
| 已完成，只读 | [`2026-07-10-framework-neutral-langgraph-evolution.md`](archive/2026-07-10-framework-neutral-langgraph-evolution.md) | 任务 34 真实咨询 Smoke Eval 已合并 |

## 已被替代

| 状态 | 计划 | 替代事实源 |
|---|---|---|
| 已替代，只读 | [`2026-07-10-model-catalog.md`](archive/2026-07-10-model-catalog.md) | v0.6 模型目录架构和当前 `docs/architecture/04-tools-models.md` |

该计划未按原复选框逐项执行；模型目录能力已通过后续架构提交和代码事实源落地，因此不再作为待办继续执行。

## 归档规则

1. 只有全部目标已完成、验证证据已记录且提交已合并到 `mvp` 的计划，才能标记为“已完成，只读”。
2. 被架构版本、代码事实源或后续计划替代的旧计划，标记为“已替代，只读”，不得伪装成已按原计划执行。
3. 归档正文不得继续创建任务分支、安装依赖或指导当前实现；后续开发只能从当前有效计划或新的版本化计划开始。
4. 历史架构正文不改写；历史计划引用统一直接指向 `archive/` 中的只读正文。
