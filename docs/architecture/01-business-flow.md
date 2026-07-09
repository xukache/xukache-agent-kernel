# 01. 业务流程与数据流

## 范围

本文定义 MVP 阶段的业务流程、数据流、badcase 回流和评测闭环。

## 政府办事大厅咨询流程

```text
群众提出问题
  ↓
识别意图：工伤认定 / 劳动能力鉴定 / 参保认定 / 待遇测算 / 其他
  ↓
抽取地区、事故场景、伤情、材料状态、工资、伤残等级等槽位
  ↓
判断信息是否足够
  ├── 不足：生成追问
  └── 足够：进入对应 Agent 链路
  ↓
调用法规 RAG、待遇测算或地区过滤工具
  ↓
聚合结果，检查引用依据、地区一致性和安全表达
  ↓
返回结论、依据、适用条件、材料建议、风险提示
```

## 工伤认定咨询

典型问题：

```text
上班路上发生交通事故，能不能认定工伤？
```

MVP 流程：

```text
IntentRouterAgent
  ↓
DomainConsultationAgent(task_type=work_injury_recognition)
  ↓
PolicyRAGAgent / PolicyRAGTool
  ↓
AnswerValidator
  ↓
PolicySafetyGuard
  ↓
ResultAggregator
```

## 劳动能力鉴定咨询

典型问题：

```text
劳动能力鉴定需要准备哪些材料？
```

MVP 流程：

```text
IntentRouterAgent
  ↓
DomainConsultationAgent(task_type=labor_capacity)
  ↓
PolicyRAGAgent / PolicyRAGTool
  ↓
输出材料清单、办理路径、注意事项
```

## 待遇测算

典型问题：

```text
四川 35 岁，伤残十级，大概能赔多少钱？
```

MVP 流程：

```text
IntentRouterAgent
  ↓
PaymentCalculationAgent
  ↓
PaymentCalculationTool
  ↓
PolicyRAGAgent 补充依据
  ↓
ResultAggregator 输出测算结果、假设条件和免责声明
```

## Badcase 回流

```text
用户负反馈 / 系统自动标记 / eval 失败
  ↓
生成候选 badcase
  ↓
补充 issue_type、expected_answer、correction_note
  ↓
必要时转成 eval case
  ↓
修复 Prompt / Tool / RAG / Rule
  ↓
运行回归评测
  ↓
标记 fixed
```

## 评测数据流

```text
eval_cases.jsonl
  ↓
EvalRunner
  ↓
AgentOrchestrator
  ↓
answer + task_state + trace + report
  ↓
指标计算
  ↓
metrics.json / badcase.jsonl
```

