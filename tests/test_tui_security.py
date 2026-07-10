from __future__ import annotations

import asyncio
import json

from ananhu_agent.models.observable_gateway import ObservableModelGateway, TransientSanitizer
from ananhu_agent.ports.model_gateway import ModelRequest, ModelResult, ModelUsage
from ananhu_agent.ports.run_event_sink import NoOpRunEventSink
from ananhu_agent.runtime import create_default_runtime
from ananhu_agent.storage.runtime_stores import (
    BadcaseStore,
    ReportStore,
    SessionStateStore,
    TaskStateStore,
    TraceRecorder,
)
from ananhu_agent.workflow.contracts import RunRequest


class _CanaryReasoningGateway:
    async def generate_structured(self, request: ModelRequest) -> ModelResult:
        return ModelResult(
            output={
                "intent": "payment_calculation",
                "confidence": 0.96,
                "slots": {
                    "province": "四川省",
                    "disability_grade": "十级",
                    "monthly_wage": 6000,
                },
                "missing_slots": [],
                "is_composite": False,
            },
            provider="provider",
            model="provider-model",
            profile=request.profile,
            usage=ModelUsage(
                input_tokens=100,
                output_tokens=20,
                total_tokens=120,
                usage_source="provider",
                reported=True,
            ),
            reasoning_content="CANARY_REASONING",
        )


def test_reasoning_canary_never_enters_runtime_persistence(tmp_path) -> None:
    runtime = create_default_runtime(tmp_path)
    runtime.intent_agent.model_gateway = ObservableModelGateway(
        _CanaryReasoningGateway(),
        events=NoOpRunEventSink(),
        sanitizer=TransientSanitizer(),
    )

    result = asyncio.run(runtime.invoke(RunRequest(
        run_id="run_reasoning_security",
        request_id="req_reasoning_security",
        session_id="sess_reasoning_security",
        turn_id=1,
        user_query="四川十级工伤，月工资6000，大概能赔多少钱？",
        created_at="2026-07-10T00:00:00+08:00",
    )))

    persisted = {
        "workflow_result": result.model_dump(mode="json"),
        "task_states": TaskStateStore(tmp_path / "task_states.jsonl").read_all(),
        "run_reports": ReportStore(tmp_path / "run_reports.jsonl").read_all(),
        "session_states": SessionStateStore(tmp_path / "session_states.jsonl").read_all(),
        "badcases": BadcaseStore(tmp_path / "badcases.jsonl").read_all(),
        "trace": TraceRecorder(tmp_path / "traces.jsonl").read_all(),
    }
    serialized = json.dumps(persisted, ensure_ascii=False)

    assert "CANARY_REASONING" not in serialized
