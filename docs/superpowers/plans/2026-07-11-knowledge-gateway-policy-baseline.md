# KnowledgeGateway 与政策基线实施计划

## 版本信息

| 字段 | 内容 |
|---|---|
| 状态 | 已完成，正在提交并合并到 `mvp` |
| 目标架构版本 | v0.8 |
| 基线架构版本 | v0.7 Textual Chat TUI |
| 任务来源 | 原框架中立 LangGraph 演进计划任务 33 |
| 分支 | `mvp-knowledge-gateway-task-33` |

## 目标

建立带可信元数据、有效期、审核和版本治理的政策语料与 KnowledgeGateway lexical baseline，
让证据能够回指原文，并为后续真实咨询 Smoke Eval 提供可重复的 RAG 评测入口。

## 实现范围

- `KnowledgeGateway`、`KnowledgeQuery`、`KnowledgeSearchResult` 和 `EvidenceItem` 项目协议。
- `policy-corpus.v1` JSONL 语料、来源 URL、审核状态、有效期、受众和证据 hash。
- 检索前可信 metadata filter 和可解释 lexical baseline。
- `PolicyRAGTool` 到 KnowledgeGateway 的兼容适配。
- `RAGEvalRunner`、Recall@K、MRR、引用支持率、可信过滤率和无结果安全率。
- Native/LangGraph 共享组合根注入的 KnowledgeGateway；模型地区槽位不能覆盖可信范围。

## 不在本任务

- 向量数据库、embedding、fusion、reranker。
- 持续抓取、自动审核和生产级政策更新服务。
- 真实模型 Smoke Eval；该能力由任务 34 单独验收。

## 验证

```bash
uv run pytest tests/test_knowledge_gateway_contract.py tests/test_policy_corpus_quality.py tests/test_rag_eval.py -v
uv run pytest -q
uv run ananhu-agent eval data/eval/eval_cases.jsonl --runtime both
```

## 验收证据

- 专项 KnowledgeGateway / corpus / RAG eval：6 passed。
- 全量测试：204 passed, 1 skipped。
- 离线 Native/LangGraph differential eval：30/30 equivalent。
- RAG baseline：Recall@K 1.0、MRR 1.0、引用支持率 1.0、可信过滤率 1.0。

## 迁移策略

现有 `PolicyRAGTool` 输入和 `documents` 输出保持兼容；旧 `policy_fixtures.jsonl` 仍可被显式
fixture_path 回放，默认组合根改用 `policy-corpus.v1.jsonl`。后续替换召回方式时必须保持
`KnowledgeSearchResult`、`EvidenceItem` 和 citation validator 契约，并用同一 RAG eval 重新校准。
