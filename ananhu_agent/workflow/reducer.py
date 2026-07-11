from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ananhu_agent.workflow.contracts import StatePatch, WorkflowPhase, WorkflowState


ALLOWED_PHASE_TRANSITIONS: dict[WorkflowPhase, set[WorkflowPhase]] = {
    WorkflowPhase.UNDERSTAND: {WorkflowPhase.MERGE_FACTS},
    WorkflowPhase.MERGE_FACTS: {WorkflowPhase.VALIDATE_FACTS},
    WorkflowPhase.VALIDATE_FACTS: {
        WorkflowPhase.CLARIFY,
        WorkflowPhase.RESOLVE_JURISDICTION,
    },
    WorkflowPhase.CLARIFY: {WorkflowPhase.COMPLETE},
    WorkflowPhase.RESOLVE_JURISDICTION: {WorkflowPhase.PLAN},
    WorkflowPhase.PLAN: {WorkflowPhase.EXECUTE},
    WorkflowPhase.EXECUTE: {WorkflowPhase.VALIDATE_EVIDENCE},
    WorkflowPhase.VALIDATE_EVIDENCE: {WorkflowPhase.COMPOSE},
    WorkflowPhase.COMPOSE: {WorkflowPhase.SAFETY},
    WorkflowPhase.SAFETY: {WorkflowPhase.COMPLETE},
    WorkflowPhase.COMPLETE: set(),
}


class ReducerResult(BaseModel):
    """Reducer 应用 patch 后的结构化结果。"""

    ok: bool = Field(description="patch 是否通过 reducer 校验。")
    applied: bool = Field(description="patch 是否真实改变了状态。")
    state: WorkflowState = Field(description="应用后的状态；失败时返回原状态副本。")
    error_code: str | None = Field(default=None, description="结构化错误码。")
    error_message: str | None = Field(default=None, description="人类可读错误描述。")


def reduce_workflow_state(state: WorkflowState, patch: StatePatch) -> ReducerResult:
    """将单个 StatePatch 合并进 WorkflowState。

    参数:
        state: 当前工作流状态，只读输入。
        patch: 阶段服务产生的状态增量。

    返回:
        `ReducerResult`。非法转换和身份不匹配以结构化失败返回，不抛业务异常。
    """

    if patch.run_id != state.run_id:
        return _failure(
            state,
            "run_id_mismatch",
            f"patch run_id {patch.run_id} does not match state run_id {state.run_id}",
        )

    if patch.patch_id in state.applied_patch_ids:
        return ReducerResult(ok=True, applied=False, state=state.model_copy(deep=True))

    if patch.source_phase is not state.phase:
        return _failure(
            state,
            "source_phase_mismatch",
            f"patch source phase {patch.source_phase.value} does not match current phase {state.phase.value}",
        )

    next_phase = patch.next_phase or state.phase
    if next_phase is not state.phase and not _can_transition(state.phase, next_phase):
        return _failure(
            state,
            "invalid_phase_transition",
            f"invalid phase transition: {state.phase.value} -> {next_phase.value}",
        )

    updated = state.model_copy(deep=True)
    updated.phase = next_phase
    updated.applied_patch_ids.append(patch.patch_id)
    updated.case_facts.update(patch.fact_updates)
    updated.capability_call_count += len(patch.capability_results)

    _overwrite_sections(updated, patch)
    updated.capability_results = _merge_by_business_id(
        updated.capability_results,
        patch.capability_results,
        key="logical_call_id",
    )
    updated.evidence = _merge_by_business_id(updated.evidence, patch.evidence, key="evidence_id")

    return ReducerResult(ok=True, applied=True, state=updated)


def _failure(state: WorkflowState, error_code: str, error_message: str) -> ReducerResult:
    """构造 reducer 结构化失败结果，避免调用方依赖异常文本。"""

    return ReducerResult(
        ok=False,
        applied=False,
        state=state.model_copy(deep=True),
        error_code=error_code,
        error_message=error_message,
    )


def _can_transition(current: WorkflowPhase, next_phase: WorkflowPhase) -> bool:
    """校验业务阶段是否允许跳转。"""

    return next_phase in ALLOWED_PHASE_TRANSITIONS[current]


def _overwrite_sections(state: WorkflowState, patch: StatePatch) -> None:
    """应用 overwrite 规则；只有 patch 显式给值时才覆盖。"""

    overwrite_fields = (
        "intent_result",
        "execution_plan",
        "draft_final_answer",
        "verification_result",
        "safety_result",
        "final_answer",
        "clarification_question",
        "status",
        "stop_reason",
    )
    for field_name in overwrite_fields:
        value = getattr(patch, field_name)
        if value is not None:
            setattr(state, field_name, value)


def _merge_by_business_id(
    existing: list[dict[str, Any]],
    updates: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    """按业务 ID 合并列表；无 ID 的记录按追加处理。"""

    merged = [dict(item) for item in existing]
    index_by_key = {
        item[key]: index for index, item in enumerate(merged) if item.get(key) is not None
    }
    for item in updates:
        business_id = item.get(key)
        if business_id is None or business_id not in index_by_key:
            index_by_key[business_id] = len(merged)
            merged.append(dict(item))
            continue
        merged[index_by_key[business_id]] = dict(item)
    return merged
