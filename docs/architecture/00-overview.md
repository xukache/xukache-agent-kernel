# 00. 项目概览

## 项目定位

安安虎工伤智能助手 Agno 多 Agent 重构版，是基于原 `ananhu_common-main` 业务能力重新设计的行业多 Agent 后端系统。

第一阶段目标是实现无前端交互式 CLI MVP，跑通：

```text
用户输入 -> 意图识别 -> Agent 路由 -> RAG / 工具调用 -> 结果聚合与校验 -> CLI 输出 -> Trace / Badcase / Eval
```

## 用户群体

- 劳动能力鉴定、工伤认定等政府办事大厅窗口。
- 普通群众的工伤政策自助咨询。
- 多地市政府小程序中的智能办事咨询助手。

## MVP 范围

MVP 只保留 4 个核心 Agent：

| Agent | 职责 |
|---|---|
| `IntentRouterAgent` | 意图识别、槽位抽取、低置信度追问 |
| `PolicyRAGAgent` | 法规、地方政策、办事指南检索和依据组织 |
| `DomainConsultationAgent` | 工伤认定、劳动能力鉴定、参保认定等文本政策咨询 |
| `PaymentCalculationAgent` | 工伤待遇测算解释和计算工具调用 |

## 非目标

- 不做前端。
- 不暴露 HTTP API。
- 不做 WebSocket。
- 不接 Dify。
- 不做复杂异步任务平台。
- 不做语音、图片、多模态输入。
- 不提前拆分专项 Agent。
- 不接 MCP / Skill 平台化扩展。

## 参考设计

- 原业务项目：`ananhu_common-main`
- MVP 原始架构快照：`TECH_ARCHITECTURE_MVP.md`
- 参考项目：饮食推荐 Agent、EchoMind、Pico

本项目只吸收参考项目中的工程治理思想，不复制其业务字段或具体能力。

