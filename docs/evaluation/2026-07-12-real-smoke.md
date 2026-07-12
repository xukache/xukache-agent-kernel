# 真实咨询 Smoke Eval 验收记录

## 状态

任务 34 已执行完成。Smoke 结果用于暴露真实失败和定位机制问题，不代表生产质量或法律结论质量。

## 执行范围

| 项目 | 内容 |
|---|---|
| 数据集 | `data/eval/real_smoke_cases.jsonl` |
| 场景数 | 8 条 |
| 运行时 | Native、LangGraph |
| Provider | OpenAI-compatible |
| Model | `doubao-seed-2-0-mini-260428` |
| Profile | `intent_fast` |
| 语料 | `policy-corpus.v1` 离线政策基线 |
| 执行命令 | `ANANHU_REAL_MODEL_SMOKE=1 uv run ananhu-agent eval data/eval/real_smoke_cases.jsonl --runtime both` |

本机通过 SOCKS 代理执行时临时使用 `uv run --with socksio`；该临时依赖未写入项目配置。

## 结果摘要

| 指标 | Native | LangGraph |
|---|---:|---:|
| 总 case | 8 | 8 |
| 答案关键片段通过 | 7/8 | 7/8 |
| 意图准确率 | 87.5% | 87.5% |
| 槽位准确率 | 2/3 | 2/3 |
| 引用支持率 | 87.5% | 87.5% |
| 安全通过率 | 100% | 100% |
| 输入 token | 3,212 | 3,212 |
| 输出 token | 4,738 | 5,025 |
| 总 token | 7,950 | 8,237 |
| 平均延迟 | 8,894.92 ms | 8,806.84 ms |
| P50 延迟 | 7,758.95 ms | 6,924.22 ms |
| P95 延迟 | 20,120.35 ms | 20,129.29 ms |
| 分类 badcase case 数 | 1 | 1 |

## 失败与差异

| 类型 | case | 结果 |
|---|---|---|
| Provider 超时 | `real_smoke_composite_001` | Native 和 LangGraph 均记录 `runtime_or_recovery_error`、`timeout_error`；评测命令仍生成完整报告 |
| 双运行时差分 | 全部 8 条 | `equivalent=0`、`different=8`；主要差异为 provider request ID、token、置信度 / missing slots，以及一次测算省份归一化结果差异 |

真实 provider 在 `temperature=0` 下仍出现结构化输出和用量差异，因此本次结果不能作为双运行时等价通过。现有差异已进入 `runtime-differential.json`，后续应单独处理真实模型确定性和差分规范化问题。

## 产物

本次本地临时产物：

```text
/tmp/ananhu-task34-smoke-final/evaluation.json
/tmp/ananhu-task34-smoke-final/runtime-differential.json
/tmp/ananhu-task34-smoke-final/native/traces.jsonl
/tmp/ananhu-task34-smoke-final/langgraph/traces.jsonl
/tmp/ananhu-task34-smoke-final/native/badcases.jsonl
/tmp/ananhu-task34-smoke-final/langgraph/badcases.jsonl
```

`evaluation.json` 使用 `evaluation.v1`，逐 case 记录模型调用、检索能力、Evidence ID、引用、Safety、Usage、延迟和失败分类；不写入 API key 或完整模型原文。

## 验收结论

- 两个 runtime 使用了相同真实 provider、profile 和离线 KnowledgeGateway。
- 模型、检索、引用、安全、token、延迟均有分层指标。
- provider 超时已转化为结构化报告和 badcase，不再以未归类 traceback 结束。
- 本次不宣称真实咨询质量通过；双运行时差分和一个真实超时问题保留为后续修复输入。
