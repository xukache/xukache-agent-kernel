import pytest

from ananhu_agent.capabilities.registry import (
    CapabilityDefinition,
    CapabilityRegistry,
)


def _definition(name: str = "knowledge.search") -> CapabilityDefinition:
    return CapabilityDefinition(
        name=name,
        description="检索政策证据",
        risk_level="read_only",
        timeout_ms=3000,
        allowed_callers=("PolicyRAGAgent",),
        required_input_keys=("query", "trusted_jurisdiction"),
        output_required_keys=("evidences", "no_result_reason"),
        handler=lambda payload: payload,
    )


def test_registry_accepts_only_explicit_capability_names():
    registry = CapabilityRegistry()
    registry.register(_definition())

    assert registry.get("knowledge.search").name == "knowledge.search"
    assert registry.get("PolicyRAG" + "Tool") is None


def test_registry_rejects_duplicate_capability_names():
    registry = CapabilityRegistry()
    registry.register(_definition())

    with pytest.raises(ValueError, match="duplicate capability"):
        registry.register(_definition())


def test_registry_returns_none_for_unknown_capability():
    registry = CapabilityRegistry()

    assert registry.get("unknown.capability") is None
