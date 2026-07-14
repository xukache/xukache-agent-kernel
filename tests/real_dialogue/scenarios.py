"""DEV_SPEC 中 RD-001 至 RD-012 的固定场景元数据。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DialogueScenario:
    """描述一个场景需要验证什么，不预填任何运行结果。"""

    test_id: str
    module: str
    raw_dialogue_input: str | tuple[str, ...]
    required_evidence: tuple[str, ...]
    blocking_conditions: tuple[str, ...]


_COMMON_EVIDENCE = (
    "test_id",
    "run_id",
    "scope",
    "model_id",
    "provider",
    "raw_dialogue_input",
    "expected_structured_assertions",
    "actual_output_summary",
    "events",
    "usage",
    "latency",
    "error_type",
    "retry_count",
    "status",
)

REAL_DIALOGUE_SCENARIOS: tuple[DialogueScenario, ...] = (
    DialogueScenario(
        "RD-001",
        "Model",
        "请计算 18 + 24，并按指定 JSON Schema 返回 result 整数。",
        _COMMON_EVIDENCE,
        ("真实 Provider 不可用", "Provider 不支持 Structured Output"),
    ),
    DialogueScenario(
        "RD-002",
        "Agent",
        "请完成任务：计算 9 + 6，并返回结构化结果。",
        _COMMON_EVIDENCE,
        ("真实 Model Adapter 尚未完成",),
    ),
    DialogueScenario(
        "RD-003",
        "Tool",
        "请使用加法工具计算 37 + 58，并告诉我最终结果。",
        _COMMON_EVIDENCE,
        ("Provider 不支持可确认的 Tool Choice",),
    ),
    DialogueScenario(
        "RD-004",
        "Memory",
        ("请记住我的项目代号是青岚。", "我的项目代号是什么？"),
        _COMMON_EVIDENCE,
        ("Memory Adapter 尚未完成",),
    ),
    DialogueScenario(
        "RD-005",
        "Runtime",
        "请使用加法工具计算 37 + 58，并告诉我最终结果。",
        _COMMON_EVIDENCE,
        ("Runtime 尚未完成",),
    ),
    DialogueScenario(
        "RD-006",
        "Workflow",
        "判断 12 是否为偶数，并执行对应分支。",
        _COMMON_EVIDENCE,
        ("Workflow 尚未完成",),
    ),
    DialogueScenario(
        "RD-007",
        "Pause / Resume",
        ("生成一条摘要，执行后续动作前等待我确认。", "确认继续。"),
        _COMMON_EVIDENCE,
        ("Runtime 不支持可序列化恢复",),
    ),
    DialogueScenario(
        "RD-008",
        "Streaming",
        "请分三步说明如何验证一个函数的输入、处理和输出。",
        _COMMON_EVIDENCE,
        ("Provider 不支持 Streaming",),
    ),
    DialogueScenario(
        "RD-009",
        "Cancellation",
        "请详细列出二十条代码审查检查项。",
        _COMMON_EVIDENCE,
        ("Provider 不支持可取消流",),
    ),
    DialogueScenario(
        "RD-010",
        "Hooks / Guardrails",
        ("请计算 2 + 3。", "BLOCK_TEST：请继续执行。"),
        _COMMON_EVIDENCE,
        ("Hooks 或 Guardrails 尚未完成",),
    ),
    DialogueScenario(
        "RD-011",
        "Workflow Parallel",
        "请分别计算 14 + 5 和 8 + 7，最后汇总两个结果。",
        _COMMON_EVIDENCE,
        ("Workflow 不支持并行",),
    ),
    DialogueScenario(
        "RD-012",
        "Retry / Idempotency",
        "请调用临时查询工具获取编号 R-12，并返回结果。",
        _COMMON_EVIDENCE,
        ("Provider 不支持可确认的 Tool Choice",),
    ),
)
