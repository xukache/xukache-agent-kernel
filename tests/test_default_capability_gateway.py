import asyncio
from dataclasses import replace
from pathlib import Path
from time import sleep

from ananhu_agent.capabilities.contracts import (
    CapabilityIdempotency,
    CapabilityRequest,
    CapabilityStatus,
)
from ananhu_agent.capabilities.default_gateway import DefaultCapabilityGateway
from ananhu_agent.capabilities.registry import CapabilityDefinition, CapabilityRegistry
from ananhu_agent.infrastructure.knowledge.lexical_gateway import LexicalKnowledgeGateway
from ananhu_agent.runtime import _default_capability_registry


class RecordingSink:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event) -> None:
        self.events.append(event)


def _request(
    capability_name: str,
    *,
    caller: str = "PolicyRAGAgent",
    attempt: int = 1,
    input: dict | None = None,
    request_id: str = "req_1",
    logical_call_id: str = "call_1",
) -> CapabilityRequest:
    return CapabilityRequest(
        run_id="run_1",
        request_id=request_id,
        session_id="sess_1",
        capability_name=capability_name,
        caller=caller,
        input=input
        or {
            "query": "工伤待遇",
            "trusted_jurisdiction": {"province": "四川省", "city": None},
        },
        node_id="execute",
        logical_call_id=logical_call_id,
        attempt=attempt,
    )


def _gateway(*, timeout_ms: int = 3000, handler=None):
    calls = {"count": 0}

    async def knowledge_handler(payload):
        calls["count"] += 1
        if handler is not None:
            return await handler(payload)
        return {"evidences": [{"evidence_id": "ev_1"}], "no_result_reason": None}

    registry = CapabilityRegistry()
    registry.register(
        CapabilityDefinition(
            name="knowledge.search",
            description="检索政策证据",
            risk_level="read_only",
            timeout_ms=timeout_ms,
            allowed_callers=("PolicyRAGAgent",),
            required_input_keys=("query", "trusted_jurisdiction"),
            output_required_keys=("evidences", "no_result_reason"),
            handler=knowledge_handler,
        )
    )
    sink = RecordingSink()
    return DefaultCapabilityGateway(registry, event_sink=sink), calls, sink


def test_gateway_returns_structured_capability_output():
    gateway, _, sink = _gateway()

    result = asyncio.run(gateway.execute(_request("knowledge.search")))

    assert result.status is CapabilityStatus.SUCCESS
    assert result.output["evidences"] == [{"evidence_id": "ev_1"}]
    assert result.logical_call_id == "call_1"
    assert result.policy.idempotency is CapabilityIdempotency.READ_ONLY_REPEATABLE
    assert [event.kind for event in sink.events] == [
        "capability_started",
        "capability_finished",
    ]


def test_legacy_capability_name_is_not_registered():
    gateway, _, sink = _gateway()

    result = asyncio.run(gateway.execute(_request("PolicyRAG" + "Tool")))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_not_registered"
    assert [event.kind for event in sink.events] == [
        "capability_started",
        "capability_failed",
    ]


def test_legacy_capability_name_is_not_affected_by_existing_cache():
    gateway, calls, _ = _gateway()
    first = asyncio.run(gateway.execute(_request("knowledge.search")))
    legacy = asyncio.run(
        gateway.execute(
            _request(
                "PolicyRAG" + "Tool",
                caller="PolicyRAGAgent",
                attempt=2,
            )
        )
    )

    assert first.status is CapabilityStatus.SUCCESS
    assert legacy.status is CapabilityStatus.FAILED
    assert legacy.error.code == "capability_not_registered"
    assert calls["count"] == 1


def test_illegal_caller_is_rejected_before_handler():
    gateway, calls, _ = _gateway()

    result = asyncio.run(
        gateway.execute(
            _request("knowledge.search", caller="PaymentCalculationAgent")
        )
    )

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "caller_not_allowed"
    assert calls["count"] == 0


def test_missing_required_input_is_rejected():
    gateway, calls, _ = _gateway()

    result = asyncio.run(
        gateway.execute(
            _request(
                "knowledge.search",
                input={"trusted_jurisdiction": {"province": "四川省"}},
            )
        )
    )

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "invalid_input_schema"
    assert calls["count"] == 0


def test_handler_timeout_is_structured():
    async def slow_handler(_payload):
        await asyncio.sleep(0.05)
        return {"evidences": [], "no_result_reason": "no_lexical_match"}

    gateway, _, sink = _gateway(timeout_ms=1, handler=slow_handler)

    result = asyncio.run(gateway.execute(_request("knowledge.search")))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_timeout"
    assert sink.events[-1].kind == "capability_failed"


def test_handler_exception_is_structured_without_leaking_exception():
    async def failing_handler(_payload):
        raise RuntimeError("secret implementation detail")

    gateway, _, sink = _gateway(handler=failing_handler)

    result = asyncio.run(gateway.execute(_request("knowledge.search")))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_handler_error"
    assert result.error.message == "能力执行失败。"
    assert "secret implementation detail" not in result.error.message
    assert sink.events[-1].kind == "capability_failed"


def test_handler_output_missing_required_field_is_structured():
    async def incomplete_handler(_payload):
        return {"evidences": []}

    gateway, _, sink = _gateway(handler=incomplete_handler)

    result = asyncio.run(gateway.execute(_request("knowledge.search")))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_output_schema_invalid"
    assert result.error.message == "能力输出缺少必填字段。"
    assert sink.events[-1].kind == "capability_failed"


def test_handler_output_must_be_an_object():
    async def invalid_handler(_payload):
        return ["not", "an", "object"]

    gateway, _, sink = _gateway(handler=invalid_handler)

    result = asyncio.run(gateway.execute(_request("knowledge.search")))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_output_schema_invalid"
    assert result.error.message == "能力输出不是结构化对象。"
    assert sink.events[-1].kind == "capability_failed"


def test_same_logical_call_cannot_be_reused_with_different_input():
    gateway, calls, sink = _gateway()
    first = asyncio.run(gateway.execute(_request("knowledge.search")))
    changed = asyncio.run(
        gateway.execute(
            _request(
                "knowledge.search",
                input={
                    "query": "另一条查询",
                    "trusted_jurisdiction": {"province": "四川省", "city": None},
                },
                attempt=2,
            )
        )
    )

    assert first.status is CapabilityStatus.SUCCESS
    assert changed.status is CapabilityStatus.FAILED
    assert changed.error.code == "logical_call_conflict"
    assert changed.reused is False
    assert calls["count"] == 1
    assert sink.events[-1].kind == "capability_failed"


def test_unregistered_capability_is_not_affected_by_existing_cache():
    gateway, calls, sink = _gateway()
    first = asyncio.run(gateway.execute(_request("knowledge.search")))
    changed = asyncio.run(
        gateway.execute(
            _request(
                "payment.calculate",
                caller="PolicyRAGAgent",
                input={"disability_grade": "十级", "monthly_wage": 6000},
                attempt=2,
            )
        )
    )

    assert first.status is CapabilityStatus.SUCCESS
    assert changed.status is CapabilityStatus.FAILED
    assert changed.error.code == "capability_not_registered"
    assert calls["count"] == 1
    assert sink.events[-1].kind == "capability_failed"


def test_same_logical_call_does_not_bypass_caller_permission():
    gateway, calls, sink = _gateway()
    first = asyncio.run(gateway.execute(_request("knowledge.search")))
    changed = asyncio.run(
        gateway.execute(
            _request(
                "knowledge.search",
                caller="PaymentCalculationAgent",
                attempt=2,
            )
        )
    )

    assert first.status is CapabilityStatus.SUCCESS
    assert changed.status is CapabilityStatus.FAILED
    assert changed.error.code == "caller_not_allowed"
    assert changed.reused is False
    assert calls["count"] == 1
    assert sink.events[-1].kind == "capability_failed"


def test_concurrent_same_logical_call_executes_handler_once():
    async def slow_handler(_payload):
        await asyncio.sleep(0.01)
        return {"evidences": [{"evidence_id": "ev_1"}], "no_result_reason": None}

    gateway, calls, _ = _gateway(handler=slow_handler)

    async def run_concurrently():
        return await asyncio.gather(
            gateway.execute(_request("knowledge.search", request_id="req_a")),
            gateway.execute(_request("knowledge.search", request_id="req_b")),
        )

    results = asyncio.run(run_concurrently())

    assert [result.status for result in results] == [
        CapabilityStatus.SUCCESS,
        CapabilityStatus.SUCCESS,
    ]
    assert sum(result.reused for result in results) == 1
    assert calls["count"] == 1


def test_output_validator_rejects_invalid_nested_evidence():
    registry = CapabilityRegistry()
    registry.register(
        CapabilityDefinition(
            name="knowledge.search",
            description="检索政策证据",
            risk_level="read_only",
            timeout_ms=3000,
            allowed_callers=("PolicyRAGAgent",),
            required_input_keys=("query", "trusted_jurisdiction"),
            output_required_keys=("evidences", "no_result_reason"),
            output_validator=_validate_test_knowledge_output,
            handler=lambda _payload: {
                "evidences": [{"evidence_id": "missing-required-fields"}],
                "no_result_reason": None,
            },
        )
    )
    gateway = DefaultCapabilityGateway(registry)

    result = asyncio.run(gateway.execute(_request("knowledge.search")))

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_output_schema_invalid"


def test_production_knowledge_output_validator_rejects_invalid_evidence():
    definition = _default_capability_registry(
        LexicalKnowledgeGateway(Path("data/policies/policy_corpus.v1.jsonl"))
    ).get("knowledge.search")
    assert definition is not None
    registry = CapabilityRegistry()
    registry.register(
        replace(
            definition,
            handler=lambda _payload: {
                "evidences": [{"evidence_id": "missing-required-fields"}],
                "corpus_version": "policy-corpus.v1",
                "applied_filters": {},
                "no_result_reason": None,
            },
        )
    )
    gateway = DefaultCapabilityGateway(registry)

    result = asyncio.run(
        gateway.execute(
            _request(
                "knowledge.search",
                input={
                    "query": "工伤待遇",
                    "trusted_jurisdiction": {"province": "四川省"},
                },
            )
        )
    )

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_output_schema_invalid"


def test_production_knowledge_output_validator_rejects_invalid_no_result_reason():
    definition = _default_capability_registry(
        LexicalKnowledgeGateway(Path("data/policies/policy_corpus.v1.jsonl"))
    ).get("knowledge.search")
    assert definition is not None
    registry = CapabilityRegistry()
    registry.register(
        replace(
            definition,
            handler=lambda _payload: {
                "evidences": [],
                "corpus_version": "policy-corpus.v1",
                "applied_filters": {},
                "no_result_reason": 123,
            },
        )
    )
    gateway = DefaultCapabilityGateway(registry)

    result = asyncio.run(
        gateway.execute(
            _request(
                "knowledge.search",
                input={
                    "query": "工伤待遇",
                    "trusted_jurisdiction": {"province": "四川省"},
                },
            )
        )
    )

    assert result.status is CapabilityStatus.FAILED
    assert result.error.code == "capability_output_schema_invalid"


def test_real_payment_capability_rejects_missing_input_and_caller():
    registry = _default_capability_registry(
        LexicalKnowledgeGateway(Path("data/policies/policy_corpus.v1.jsonl"))
    )
    gateway = DefaultCapabilityGateway(registry)

    success = asyncio.run(
        gateway.execute(
            _request(
                "payment.calculate",
                caller="PaymentCalculationAgent",
                input={"disability_grade": "十级", "monthly_wage": 6000},
            )
        )
    )
    missing = asyncio.run(
        gateway.execute(
            _request(
                "payment.calculate",
                caller="PaymentCalculationAgent",
                input={"monthly_wage": 6000},
                request_id="req_missing",
            )
        )
    )
    forbidden = asyncio.run(
        gateway.execute(
            _request(
                "payment.calculate",
                caller="PolicyRAGAgent",
                input={"disability_grade": "十级", "monthly_wage": 6000},
                request_id="req_forbidden",
            )
        )
    )

    assert success.status is CapabilityStatus.SUCCESS
    assert success.output["items"][0]["amount"] == 42000
    assert missing.error.code == "invalid_input_schema"
    assert forbidden.error.code == "caller_not_allowed"


def test_registered_capability_change_returns_logical_call_conflict():
    registry = _default_capability_registry(
        LexicalKnowledgeGateway(Path("data/policies/policy_corpus.v1.jsonl"))
    )
    gateway = DefaultCapabilityGateway(registry)
    knowledge = asyncio.run(
        gateway.execute(
            _request(
                "knowledge.search",
                logical_call_id="shared_call",
            )
        )
    )
    payment = asyncio.run(
        gateway.execute(
            _request(
                "payment.calculate",
                caller="PaymentCalculationAgent",
                input={"disability_grade": "十级", "monthly_wage": 6000},
                logical_call_id="shared_call",
                request_id="req_payment",
                attempt=2,
            )
        )
    )

    assert knowledge.status is CapabilityStatus.SUCCESS
    assert payment.status is CapabilityStatus.FAILED
    assert payment.error.code == "logical_call_conflict"


def test_same_logical_call_reuses_result():
    gateway, calls, sink = _gateway()
    first = asyncio.run(gateway.execute(_request("knowledge.search", attempt=1)))
    retry = asyncio.run(gateway.execute(_request("knowledge.search", attempt=2)))

    assert first.status is CapabilityStatus.SUCCESS
    assert retry.status is CapabilityStatus.SUCCESS
    assert retry.reused is True
    assert retry.attempt == 2
    assert calls["count"] == 1
    assert [event.kind for event in sink.events].count("capability_finished") == 2


def _validate_test_knowledge_output(output):
    if not isinstance(output["evidences"], list):
        raise TypeError("evidences must be a list")
    for evidence in output["evidences"]:
        if set(evidence) != {"evidence_id", "content"}:
            raise ValueError("invalid evidence shape")
