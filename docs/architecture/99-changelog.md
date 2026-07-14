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

## 本次变更结论

| 检查项 | 结论 |
|---|---|
| 六个核心原语、模块边界、依赖方向和公共契约 | 未改变 |
| 架构版本正文 | 不创建 |
| 开发规格版本 | 不新增 |
| A3 实施状态 | 已完成 |
| Kernel 代码目录 | 不创建 |
| 物理目录和公开导入路径 | 已由 A3 确认 |
| A4 工程与测试基座 | 已完成 |
