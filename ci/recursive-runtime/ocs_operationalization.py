from dataclasses import dataclass
from typing import Dict, FrozenSet


@dataclass(frozen=True)
class OCSRuntimeBinding:
    ocs_id: str
    role: str
    allowed_runtime_capabilities: FrozenSet[str]
    forbidden_runtime_capabilities: FrozenSet[str]
    production_effects: bool = False
    authority_expansion: bool = False


COMMON_ALLOWED = frozenset({
    "SELF_INSPECT",
    "REFLECT",
    "CONTINUE",
    "HOLD",
    "STOP",
    "ESCALATE",
})

COMMON_FORBIDDEN = frozenset({
    "SELF_PROMOTE",
    "ASSURANCE_BYPASS",
    "FOUNDER_GATE_BYPASS",
    "AUTHORITY_EXPANSION",
    "PRODUCTION_EFFECT",
    "MULTI_PROVIDER_EXPANSION",
})


def _binding(ocs_id: str, role: str, extra_allowed=()) -> OCSRuntimeBinding:
    return OCSRuntimeBinding(
        ocs_id=ocs_id,
        role=role,
        allowed_runtime_capabilities=frozenset(set(COMMON_ALLOWED) | set(extra_allowed)),
        forbidden_runtime_capabilities=COMMON_FORBIDDEN,
    )


OCS_RUNTIME_BINDINGS: Dict[str, OCSRuntimeBinding] = {
    "NOESIS": _binding("NOESIS", "orchestration/meta-architecture", {"DELEGATE"}),
    "DEDALA": _binding("DEDALA", "technical/adversarial assurance", {"DELEGATE"}),
    "SYNESIS": _binding("SYNESIS", "independent institutional assurance"),
    "SOFIA": _binding("SOFIA", "software implementation", {"DELEGATE"}),
    "IRIS": _binding("IRIS", "ux/ui and founder experience", {"DELEGATE"}),
    "LYRA": _binding("LYRA", "brand/language/semantic identity", {"DELEGATE"}),
    "AGORA": _binding("AGORA", "qa/reproducibility/ci evidence", {"DELEGATE"}),
    "AURI": _binding("AURI", "administrative continuity/records", {"DELEGATE"}),
    "METIS": _binding("METIS", "research/strategy/intelligence", {"DELEGATE"}),
    "SYNERGEIA": _binding("SYNERGEIA", "gtm/channels/activation/distribution", {"DELEGATE"}),
}


def get_binding(ocs_id: str) -> OCSRuntimeBinding:
    key = ocs_id.strip().upper()
    if key not in OCS_RUNTIME_BINDINGS:
        raise KeyError(f"UNKNOWN_OCS:{ocs_id}")
    return OCS_RUNTIME_BINDINGS[key]


def assert_operationalization_invariants() -> None:
    assert len(OCS_RUNTIME_BINDINGS) == 10
    for binding in OCS_RUNTIME_BINDINGS.values():
        assert binding.production_effects is False
        assert binding.authority_expansion is False
        assert "PRODUCTION_EFFECT" in binding.forbidden_runtime_capabilities
        assert "AUTHORITY_EXPANSION" in binding.forbidden_runtime_capabilities
        assert "SELF_PROMOTE" in binding.forbidden_runtime_capabilities
        assert "FOUNDER_GATE_BYPASS" in binding.forbidden_runtime_capabilities
