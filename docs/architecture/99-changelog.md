# 架构文档变更记录

本文件记录架构导航和分册的维护变化。系统边界的正式变化必须进入 `docs/architecture/versions/`，不能只记录在这里。

| 日期 | 类型 | 变更内容 | 影响文档 | 是否改变架构边界 |
|---|---|---|---|---|
| 2026-07-13 | 新增 | 建立技术架构总入口，统一事实源优先级、阅读顺序和维护规则 | `docs/architecture.md` | 否 |
| 2026-07-13 | 新增 | 建立架构总览、模块边界、运行数据流、公共契约、演进规则和变更记录分册 | `docs/architecture/*.md` | 否 |
| 2026-07-13 | 新增 | 建立公共接口契约入口，明确当前只有 Python Programmatic Interface，尚无 HTTP、WebSocket 或 MCP 外部 API | `docs/api-contracts.md` | 否 |
| 2026-07-13 | 新增 | 建立后端开发规范，集中记录 Python、依赖方向、类型、异步、错误、状态和测试规则 | `docs/backend-conventions.md` | 否 |
| 2026-07-13 | 更新 | 补充 Coding Agent 修改前阅读路径、文档事实源和纯文档治理分支规则 | `AGENTS.md` | 否 |
| 2026-07-13 | 更新 | 补充项目文档索引、架构分册索引和文档使用规则 | `README.md`、`docs/architecture/README.md` | 否 |
| 2026-07-13 | 确认 | 确认 `src/agent_kernel` Kernel 包、Adapter / Application / Interface 顶层命名空间、公开导入边界和测试分层 | `docs/superpowers/specs/2026-07-13-agent-kernel-physical-layout-import-paths-a3.md` | 否 |
| 2026-07-14 | 新增 | 建立 Python 3.11、uv、pytest 和 AST Architecture Test 工程基座；仅创建空包入口，不声明 Core 实现 | `pyproject.toml`、`uv.lock`、`src/agent_kernel/__init__.py`、`tests/`、`docs/superpowers/specs/2026-07-14-agent-kernel-engineering-test-foundation-a4.md` | 否 |
| 2026-07-14 | 新增 | 建立 RD 场景注册、隔离 `run_id/scope`、结构化证据、状态约束和凭证脱敏写入基座；不执行真实 Provider | `tests/real_dialogue/`、`tests/support/`、`.gitignore`、`docs/superpowers/specs/2026-07-14-agent-kernel-real-dialogue-evidence-foundation-a5.md` | 否 |
| 2026-07-14 | 确认 | 建立 `agent_kernel.model` 的 Provider Neutral ModelRequest / ModelResponse 数据协议；只定义 Schema，不定义 Provider 调用行为 | `src/agent_kernel/model/`、`docs/architecture/03-public-contracts.md`、`docs/superpowers/specs/2026-07-14-agent-kernel-model-request-response-b1.md` | 否 |
| 2026-07-14 | 确认 | 建立 Model Protocol、异步 generate / stream 合同和 Provider Neutral 错误分类；不接入真实 Provider | `src/agent_kernel/model/`、`tests/contract/model/`、`docs/superpowers/specs/2026-07-14-agent-kernel-model-contract-errors-b2.md` | 否 |
| 2026-07-14 | 新增 | 建立 Volcengine Ark HTTP Model Adapter、配置校验、响应归一化和错误映射；真实 Smoke 尚未运行，Streaming 留给 B5 | `src/adapters/model/volcengine.py`、`tests/integration/model/`、`docs/superpowers/specs/2026-07-14-agent-kernel-volcengine-adapter-b3.md` | 否 |
| 2026-07-14 | 更新 | 将 Provider、模型、Endpoint、超时和能力配置统一收敛到 YAML Model Catalog；环境变量仅定位 Catalog 和注入密钥 | `config/models.yaml`、`src/adapters/model/volcengine.py`、`README.md`、`DEV_SPEC.md` | 否 |
| 2026-07-14 | 确认 | 用户确认 B3 Volcengine Ark Model Adapter 完成；真实 Provider Smoke 仍保持 `NOT RUN`，不等同于 RD-001 通过 | `DEV_SPEC.md`、`docs/superpowers/specs/2026-07-14-agent-kernel-volcengine-adapter-b3.md` | 否 |
| 2026-07-14 | 新增 | 开始 B4 结构化输出转换：显式 Schema 请求的 JSON 解析、本地 Schema 校验和格式错误映射；普通文本、Tool Call 与 Streaming 边界保持不变 | `src/adapters/model/volcengine.py`、`tests/integration/model/test_volcengine_adapter.py`、`docs/superpowers/specs/2026-07-14-agent-kernel-structured-output-b4.md` | 否 |
| 2026-07-14 | 确认 | 用户确认 B4 结构化输出转换完成；真实网络 Smoke 和 RD-001 仍由后续 B6 验收 | `DEV_SPEC.md`、`docs/superpowers/specs/2026-07-14-agent-kernel-structured-output-b4.md` | 否 |
| 2026-07-14 | 新增 | 开始 B5 Provider Streaming 转换：接入 SSE 文本、Tool Call、结构化输出收尾、usage 和结束原因归一化 | `src/adapters/model/volcengine.py`、`tests/integration/model/test_volcengine_adapter.py`、`docs/superpowers/specs/2026-07-14-agent-kernel-provider-streaming-b5.md` | 否 |
| 2026-07-14 | 确认 | 用户确认 B5 Provider Streaming 转换完成；真实 Provider Smoke、Runtime 治理和 RD-001 仍由后续任务验收 | `DEV_SPEC.md`、`docs/superpowers/specs/2026-07-14-agent-kernel-provider-streaming-b5.md` | 否 |
| 2026-07-14 | 新增 | 开始 B6 RD-001 真实模型验收；新增真实 Provider 门禁测试、结构化结果证据和 usage 脱敏修复 | `tests/real_dialogue/test_rd001_model.py`、`tests/support/real_dialogue_evidence.py`、`docs/superpowers/specs/2026-07-14-agent-kernel-real-model-acceptance-b6.md` | 否 |
| 2026-07-14 | 确认 | 用户确认 B6 完成；RD-001 已通过真实 Volcengine Provider，阶段 B Model MVP 完成 | `DEV_SPEC.md`、`docs/superpowers/specs/2026-07-14-agent-kernel-real-model-acceptance-b6.md` | 否 |
| 2026-07-14 | 更新 | 同步 B6 后活动架构、开发规格和项目入口文档；修正 Model MVP、真实 RD-001、实现边界及已删除 `mvp` 分支描述 | `README.md`、`DEV_SPEC.md`、`docs/architecture.md`、`docs/architecture/00-overview.md`、`docs/dev-spec/README.md` | 否 |
| 2026-07-15 | 架构基线 | 确认 Memory 会话级、用户级和项目 / 共享级 scope，冻结默认隔离、显式跨会话共享、跨 scope 提升和来源追踪；发布首个完整架构版本 v0.1 | `DEV_SPEC.md`、`docs/architecture/*.md`、`docs/architecture/versions/v0.1-memory-scope-sharing.md`、`docs/dev-spec/versions/v0.26-memory-scope-sharing.md` | 是 |

## 2026-07-14 变更结论

| 检查项 | 结论 |
|---|---|
| 六个核心原语、模块边界、依赖方向和公共契约 | 未改变 |
| 架构版本正文 | 不创建 |
| 开发规格版本 | 不新增 |
| A3 实施状态 | 已完成 |
| Kernel 代码目录 | 不创建 |
| 物理目录和公开导入路径 | 已由 A3 确认 |
| A4 工程与测试基座 | 已完成 |
| A5 真实对话证据基座 | 已完成 |
| B1 ModelRequest / ModelResponse | 已完成 |
| B2 Model Contract 与错误语义 | 已完成 |
| B3 Volcengine Ark Model Adapter | 已完成 |
| B4 结构化输出转换 | 已完成 |
| B5 Provider Streaming 转换 | 已完成 |
| B6 RD-001 真实模型验收 | 已完成 |

## 2026-07-15 变更结论

| 检查项 | 结论 |
|---|---|
| 六个核心原语数量和总体依赖方向 | 未改变 |
| Memory 数据所有权和运行链路 | 补充多层 scope、显式读写目标和提升语义 |
| 架构版本正文 | 新增 `v0.1-memory-scope-sharing.md` |
| 开发规格版本 | 新增 `v0.26-memory-scope-sharing.md` |
| E1-E6 实施状态 | 保持待开始 |
| Kernel Memory 代码目录 | 不创建 |
| 第一阶段 Memory Adapter | 仍为 In-memory Adapter |
| 持久化、向量库和语义检索 | 不引入 |
