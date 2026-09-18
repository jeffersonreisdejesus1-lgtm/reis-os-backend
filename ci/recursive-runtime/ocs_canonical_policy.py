from dataclasses import dataclass
from typing import Dict, FrozenSet

POLICY_ID = "FOUNDER-OCS-RUNTIME-BINDING-POLICY-V1-001"
POLICY_SOURCE_REF = "FOUNDER_ROLE_REGISTRY::REIS_OS_10_OCS"
POLICY_VERSION = 1

@dataclass(frozen=True)
class CanonicalOCSPolicy:
    ocs_id: str
    role: str
    may_delegate: bool

CANONICAL_OCS_POLICY: Dict[str, CanonicalOCSPolicy] = {
    "NOESIS": CanonicalOCSPolicy("NOESIS", "orchestration/meta-architecture", True),
    "DEDALA": CanonicalOCSPolicy("DEDALA", "technical/adversarial assurance", True),
    "SYNESIS": CanonicalOCSPolicy("SYNESIS", "independent institutional assurance", False),
    "SOFIA": CanonicalOCSPolicy("SOFIA", "software implementation", True),
    "IRIS": CanonicalOCSPolicy("IRIS", "ux/ui and founder experience", True),
    "LYRA": CanonicalOCSPolicy("LYRA", "brand/language/semantic identity", True),
    "AGORA": CanonicalOCSPolicy("AGORA", "qa/reproducibility/ci evidence", True),
    "AURI": CanonicalOCSPolicy("AURI", "administrative continuity/records", True),
    "METIS": CanonicalOCSPolicy("METIS", "research/strategy/intelligence", True),
    "SYNERGEIA": CanonicalOCSPolicy("SYNERGEIA", "gtm/channels/activation/distribution", True),
}

GLOBAL_FORBIDDEN: FrozenSet[str] = frozenset({
    "SELF_PROMOTE", "ASSURANCE_BYPASS", "FOUNDER_GATE_BYPASS",
    "AUTHORITY_EXPANSION", "PRODUCTION_EFFECT", "MULTI_PROVIDER_EXPANSION",
})
