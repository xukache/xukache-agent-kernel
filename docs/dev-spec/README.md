# 开发规格版本目录

> 当前完整开发规格：[`../../DEV_SPEC.md`](../../DEV_SPEC.md)

## 目录职责

`DEV_SPEC.md` 维护当前完整开发规格。本文档只负责说明版本增量文档如何组织，不复制完整规格内容。

版本增量文档放在：

```text
docs/dev-spec/versions/
  v<版本号>-<主题>.md
```

示例：

```text
docs/dev-spec/versions/
  v0.4-clean-kernel-baseline.md
  v0.15-kernel-design-baseline.md
  v0.16-full-spec-structure-baseline.md
```

## 什么时候新增版本文档

以下情况需要新增版本增量文档：

- 新增 Kernel 能力。
- 改变原语职责或模块边界。
- 改变运行链路、存储、外部接口或部署方式。
- 新增业务 Application。
- 新增会影响测试、迁移或兼容性的功能。

只修改错别字、链接或不改变语义的表达时，直接更新 `DEV_SPEC.md` 即可。

同一设计或架构里程碑内的多个模块确认，合并记录在一份版本增量文档中，不为每个模块单独创建版本。只有形成新的独立变更基线时，才递增版本号。

## 版本文档要求

每份版本文档必须说明：

1. 版本和主题。
2. 基线版本。
3. 新增内容。
4. 修改内容。
5. 受影响模块。
6. 兼容性和迁移策略。
7. 测试和验收标准。
8. 对应架构版本、架构分册和实施计划。
9. 已知限制。

版本文档只记录增量，不复制 `DEV_SPEC.md` 全文。架构边界变化时，必须同时创建 `docs/architecture/versions/` 下的完整架构版本正文，并更新架构入口和 `99-changelog.md`。

## 变更关系

```text
DEV_SPEC.md
  -> 当前完整开发规格

docs/dev-spec/versions/
  -> 每个版本的新增和变更

docs/architecture/versions/
  -> 改变系统边界时的新架构完整快照

docs/superpowers/specs/
  -> 模块确认和设计记录

docs/superpowers/plans/
  -> 实现阶段的可执行任务
```

四类文档职责不同，不能互相替代。

## 当前版本

当前开发规格版本为 `v0.16`，六个 Core 原语、Execution、支撑协议、Applications 和 Interfaces 边界均已确认，已按参考规格完成全章详细结构升级，待用户审查。当前尚未建立新的架构版本；架构版本应在真实 Agent 闭环和 Contract / Integration / Architecture Tests 通过后创建。

## 版本索引

| 版本 | 主题 | 状态 |
|---|---|---|
| `v0.4` | 全新 Kernel 清理与重构基线 | 已归档基线 |
| `v0.15` | Core、Execution、支撑协议、Application 和 Interface 的完整设计基线 | 已建立基线 |
| `v0.16` | 全章详细规格结构、真实模型前置验证和实现排期基线 | 待用户审查 |
