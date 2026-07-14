# Agent Kernel A5 真实对话证据基座记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | A5：建立真实对话证据基座 |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/a5-real-dialogue-evidence-foundation` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | A1、A2、A3、A4 已完成 |

本记录只建立真实对话验收的测试支持和证据入口，不实现真实 Model、
Agent、Tool、Memory、Runtime 或 Workflow。

## 2. 任务目标

A5 将第四章的真实对话规则落实为可复用的确定性测试基座：

- 固定 RD-001 至 RD-012 的场景入口。
- 每次场景运行生成独立的 `run_id` 和 `scope`。
- 用结构化字段记录真实运行结果。
- 只允许 `PASS`、`FAIL`、`BLOCKED`、`NOT RUN` 四种状态。
- 失败和阻塞证据必须包含可复现信息。
- 凭证、Bearer Token、常见 API Key 和敏感字段必须脱敏。
- 没有真实 Provider 时不生成模拟 `PASS` 证据。

## 3. 已确认文件

```text
tests/
├── __init__.py
├── real_dialogue/
│   ├── __init__.py
│   ├── scenarios.py
│   └── test_scenario_registry.py
└── support/
    ├── __init__.py
    ├── real_dialogue_evidence.py
    └── test_real_dialogue_evidence.py
```

运行产物默认写入：

```text
artifacts/real-dialogue/<test_id>/<run_id>.json
```

该目录已加入 `.gitignore`。受控环境可以通过
`ANANHU_REAL_DIALOGUE_EVIDENCE_DIR` 指定其他工件目录。

## 4. 证据模型

`DialogueEvidence` 覆盖第四章规定的最小字段：

```text
test_id
run_id
scope
model_id
provider
raw_dialogue_input
expected_structured_assertions
actual_output_summary
events
usage
latency
error_type
retry_count
status
```

`FAIL` 和 `BLOCKED` 必须额外提供：

```text
expected
actual
failure_stage
reproducible_command
```

Evidence Recorder 使用 Pydantic v2 进行结构校验，并以 UTF-8、排序键和
缩进 JSON 原子写入。证据支持层不进入 `agent_kernel` 公共 API。

## 5. 场景注册表

`REAL_DIALOGUE_SCENARIOS` 固定注册 `RD-001` 至 `RD-012`，每个场景保存：

- 场景 ID 和首次引入模块。
- DEV_SPEC 规定的原始输入，双轮场景用有序输入序列表示。
- 必须具备的证据字段。
- Provider、模块或能力不可用时的阻塞条件。

注册表只描述场景，不预填 Tool 参数、Memory 内容、Workflow 分支、步骤
结果或最终答案。真实场景实现由 B-G 任务按模块逐项增加。

## 6. 脱敏规则

证据写入前递归处理字典、列表和文本：

- 敏感字段名包含 `api_key`、`authorization`、`password`、`secret` 或
  `token` 时替换为 `[REDACTED]`。
- `Bearer <value>` 和常见 `sk-*` Key 文本被替换。
- 脱敏发生在 Pydantic 校验和 JSON 写入之前。

该规则是通用基线，不能替代真实场景对用户隐私和 Prompt 的最小化设计。

## 7. 验证结果

| 命令 | 结果 |
|---|---|
| `uv run pytest -q` | 通过，10 passed |
| `uv lock --check` | 通过 |
| `git diff --check` | 通过 |

本任务没有执行真实 Provider，因此当前没有任何 `RD-*` 真实场景证据可标记
为 `PASS`；真实 Provider、凭证和 Model Adapter 将由 B-G 任务逐步接入。

## 8. 与架构和规格的关系

- A5 不改变六个 Core、依赖方向、运行链路或公开协议，因此不创建架构版本正文。
- `DEV_SPEC.md` 的 A5 状态已在用户确认后更新为 `[x]`。
- 本任务只建立测试支持代码，不创建 Kernel Core 目录。
- 本任务关联 `RD-001` 至 `RD-012` 的公共证据基座，不声明任何模块实现完成。

## 9. 已知限制

- 当前没有真实 Provider 执行器；测试只验证场景元数据和证据写入行为。
- 证据脱敏是通用基线，后续 Adapter 必须按实际 Provider 响应字段补充白名单提取。
- 真实 RD 测试必须在对应模块完成后新增，并累计回归历史场景。
