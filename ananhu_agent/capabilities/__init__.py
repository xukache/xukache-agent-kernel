"""框架中立能力协议。"""

from ananhu_agent.capabilities.contracts import (
    CapabilityError,
    CapabilityGateway,
    CapabilityIdempotency,
    CapabilityPolicy,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
)
from ananhu_agent.capabilities.registry import CapabilityDefinition, CapabilityRegistry

__all__ = [
    "CapabilityError",
    "CapabilityGateway",
    "CapabilityIdempotency",
    "CapabilityPolicy",
    "CapabilityRequest",
    "CapabilityResult",
    "CapabilityStatus",
    "CapabilityDefinition",
    "CapabilityRegistry",
]
