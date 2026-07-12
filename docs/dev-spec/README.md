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
  v0.5-agent-kernel.md
  v0.6-work-injury-application.md
```

## 什么时候新增版本文档

以下情况需要新增版本增量文档：

- 新增 Kernel 能力。
- 改变原语职责或模块边界。
- 改变运行链路、存储、外部接口或部署方式。
- 新增业务 Application。
- 新增会影响测试、迁移或兼容性的功能。

只修改错别字、链接或不改变语义的表达时，直接更新 `DEV_SPEC.md` 即可。

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

当前开发规格版本为 `v0.4`，处于新 Kernel 重构起点，尚未建立新的架构版本。下一份版本增量文档应在第一个经过确认的 Kernel 版本或架构版本建立时创建。
