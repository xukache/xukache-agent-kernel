# C5 RD-002 Agent 真实验收计划

> 本计划只执行已由用户确认的 C5 真实验收方案，不修改 Agent 执行契约。

## 步骤

1. 新增 RD-002 场景测试和结构化证据写入。
2. 先运行关闭真实 Smoke 的确定性门禁，确认记录 `NOT RUN`。
3. 使用真实 Provider 运行 RD-001、RD-002 累计回归。
4. 检查每个证据文件的实际 `status`，不能只看 pytest 结果。
5. 更新 C5 活动文档为“已实现，待用户验收”。
6. 用户确认后再本地提交；不推送任务分支。

## 验收命令

```bash
export ANANHU_REAL_MODEL_SMOKE=1
unset ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
uv run pytest -q \
  tests/real_dialogue/test_rd001_model.py \
  tests/real_dialogue/test_rd002_agent.py
```
