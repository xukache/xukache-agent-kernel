# 公共接口契约

本文档是公共调用契约的导航入口。当前项目没有 HTTP、REST、WebSocket 或 MCP 外部 API，因此不创建虚构的路由、请求地址、状态码或领域接口分册。

## 当前调用面

第一阶段只提供 Python Programmatic Interface：

```text
调用者
  -> Application / Test Composition Root
  -> 创建 Definition 并注入 Adapter
  -> Runtime 接收结构化 RunRequest
  -> Agent 或 Workflow 执行
  -> 返回 Events 和结构化 Result
```

这里的 Kernel Protocol 是 Python 行为契约，不是网络 API。A3 已确认 `agent_kernel` 及其稳定子包为公开导入路径基线；具体模块字段和方法签名由后续 B-G 任务确认。

## 当前契约事实源

| 契约范围 | 事实源 |
|---|---|
| 六个 Core 的语义级输入、输出和非职责 | `DEV_SPEC.md` 第 5.3 节 |
| Agent、Tool、Memory、Workflow 数据流 | `DEV_SPEC.md` 第 5.4 节 |
| Protocol、Definition、Schema、Error、State 规则 | `DEV_SPEC.md` 第 5.7 节和 A2 确认记录 |
| 具体模块字段、状态枚举和错误捕获层级 | 后续 B-G 对应任务，当前不得自行补全 |

摘要见 [`docs/architecture/03-public-contracts.md`](architecture/03-public-contracts.md)。

## 稳定边界

- Model、Tool、Memory 和 Runtime 等可替换能力通过 `typing.Protocol` 表达行为。
- Definition 是只读装配对象，不是调用输入，也不承诺整体 JSON 序列化。
- Input、Result、Event、State 和跨 Adapter 数据必须使用严格 Schema，并能按所属边界稳定序列化。
- Provider SDK、Backend 对象、凭证、callable 和内部 Exception 不得进入公共 Schema。
- `KernelError` 负责 Python 运行时传播，`ErrorInfo` 负责公开、脱敏、可序列化的失败证据。

## 新增外部接口的门禁

新增 CLI、HTTP、WebSocket、MCP 或其他 Interface 前必须：

1. 先在 `DEV_SPEC.md` 确认调用者、输入输出、错误映射、安全边界和非目标。
2. 判断是否改变外部接口或部署方式；若改变，创建新的架构版本正文。
3. 在 `docs/api-contracts/` 下创建对应领域契约，记录协议、版本、Schema、错误和兼容策略。
4. Interface 只能转换输入、转发事件、序列化结果和映射错误，不能承载 Kernel 业务语义。
5. 使用契约测试证明 Interface 不泄漏 Adapter 或 Provider 类型。

在首个外部接口确认前，不创建空的 `docs/api-contracts/` 目录。
