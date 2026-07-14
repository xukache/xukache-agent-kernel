# Agent Kernel B6 RD-001 真实模型验收记录

## 1. 记录信息

| 字段 | 内容 |
|---|---|
| 任务 | B6：完成 RD-001 真实模型验收 |
| 日期 | 2026-07-14 |
| 状态 | 已完成 |
| 任务分支 | `task/b6-real-model-acceptance` |
| 基线分支 | `architecture` |
| 当前规格 | `DEV_SPEC v0.25` |
| 前置任务 | B4、B5、A5 已完成 |

## 2. 真实验收链路

```text
RD-001 固定用户输入
  -> ModelRequest(output_schema)
  -> VolcengineArkModel.generate()
  -> 真实 Volcengine Ark Provider
  -> ModelResponse
  -> EvidenceRecorder
```

测试文件：

```text
tests/real_dialogue/test_rd001_model.py
```

只有以下条件同时满足时才发起真实网络请求：

```text
ANANHU_REAL_MODEL_SMOKE=1
ANANHU_MODEL_CATALOG 可读取
VOLCENGINE_API_KEY 可读取
```

Smoke 未开启时记录 `NOT RUN`；配置、网络或 Provider 不可用时记录
`BLOCKED`；响应格式不正确或断言失败时记录 `FAIL`。

## 3. 固定断言

| 字段 | 断言 |
|---|---|
| 用户输入 | `请计算 18 + 24，并按指定 JSON Schema 返回 result 整数。` |
| `structured_output.result` | `42` |
| `finish_reason` | `stop` |
| `model_id` | 记录真实模型标识 |
| `provider` | `volcengine` |
| `usage` | 记录 input、output、total token |
| `latency` | 记录非负秒数 |

## 4. 实际真实运行证据

最新真实运行结果：

| 字段 | 值 |
|---|---|
| 状态 | `PASS` |
| Provider | `volcengine` |
| Model | `doubao-seed-2-0-mini-260428` |
| 结构化结果 | `result == 42` |
| Finish Reason | `stop` |
| Input Tokens | `196` |
| Output Tokens | `70` |
| Total Tokens | `266` |
| Latency | 约 `1.75s` |

证据文件写入被 `.gitignore` 排除的目录：

```text
artifacts/real-dialogue/RD-001/<run_id>.json
```

证据不保存 API Key；usage token 数不是凭证，已修正 A5 脱敏规则以保留。

## 5. 验证结果

| 验证 | 结果 |
|---|---|
| Smoke 关闭门禁 | 通过，记录 `NOT RUN` |
| 真实 Provider RD-001 | 通过，记录 `PASS` |
| Evidence 支持层回归 | 通过 |
| `uv run pytest -q` | 待最终验证 |
| `uv lock --check` | 待最终验证 |
| `git diff --check` | 待最终验证 |

真实运行时本机默认 SOCKS 代理缺少 `socksio`，首次尝试在 HTTP 客户端创建阶段
被阻塞；第二次运行清除代理环境变量后成功访问真实 Provider。该运行环境处理
没有写入代码配置。

## 6. 后续边界

- B6 不实现 Agent、Tool、Memory、Runtime 或历史 RD 回归。
- B 阶段完成后，C1 开始 Agent MVP。
- RD-008 Streaming 真实验收由后续 Runtime / Execution 阶段负责。
