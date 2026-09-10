from dataclasses import dataclass
from typing import Dict, FrozenSet

from ocs_canonical_policy import CANONICAL_OCS_POLICY, GLOBAL_FORBIDDEN, POLICY_ID, POLICY_SOURCE_REF


@dataclass(frozen=True)
class OCSRuntimeBinding:
    ocs_id: str
    role: str
    allowed_runtime_capabilities: FrozenSet[str]
    forbidden_runtime_capabilities: FrozenSet[str]
    canonical_policy_id: str
    canonical_source_ref: str
    production_effects: bool = False
    authority_expansion: bool = False


COMMON_ALLOWED = frozenset({
    "SELF_INSPECT", "REFLECT", "CONTINUE", "HOLD", "STOP", "ESCALATE",
})


def _binding(ocs_id: str) -> OCSRuntimeBinding:
    policy = CANONICAL_OCS_POLICY[ocs_id]
    allowed = set(COMMON_ALLOWED)
    if policy.may_delegate:
        allowed.add("DELEGATE")
    return OCSRuntimeBinding(
        ocs_id=ocs_id,
        role=policy.role,
        allowed_runtime_capabilities=frozenset(allowed),
        forbidden_runtime_capabilities=GLOBAL_FORBIDDEN,
        canonical_policy_id=POLICY_ID,
        canonical_source_ref=POLICY_SOURCE_REF,
    )


OCS_RUNTIME_BINDINGS: Dict[str, OCSRuntimeBinding] = {
    ocs_id: _binding(ocs_id) for ocs_id in CANONICAL_OCS_POLICY
}


def get_binding(ocs_id: str) -> OCSRuntimeBinding:
    key = ocs_id.strip().upper()
    if key not in OCS_RUNTIME_BINDINGS:
        raise KeyError(f"UNKNOWN_OCS:{ocs_id}")
    binding = OCS_RUNTIME_BINDINGS[key]
    policy = CANONICAL_OCS_POLICY[key]
    if binding.role != policy.role or binding.ocs_id != policy.ocs_id:
        raise RuntimeError(f"CANONICAL_BINDING_MISMATCH:{key}")
    return binding


class OCSRuntimeEnforcer:
    def binding_for_actor(self, actor):
        return get_binding(actor.identity_id)

    def authorize_outcome(self, actor, outcome):
        binding = self.binding_for_actor(actor)
        name = outcome.value if hasattr(outcome, "value") else str(outcome)
        if name not in binding.allowed_runtime_capabilities:
            return False, f"OCS_CAPABILITY_FORBIDDEN:{name}"
        return True, "OK"

    def authorize_effect(self, actor, capability: str):
        binding = self.binding_for_actor(actor)
        if capability in binding.forbidden_runtime_capabilities:
            return False, f"OCS_CAPABILITY_FORBIDDEN:{capability}"
        if capability not in binding.allowed_runtime_capabilities:
            return False, f"OCS_CAPABILITY_UNBOUND:{capability}"
        return True, "OK"

    def authorize_delegate_request(self, actor, request):
        ok, detail = self.authorize_effect(actor, "DELEGATE")
        if not ok:
            return ok, detail
        if not request.requested_scopes.issubset(actor.authority.scopes):
            return False, "OCS_SCOPE_ESCAPE"
        if not request.requested_capabilities.issubset(actor.capability.capabilities):
            return False, "OCS_CAPABILITY_ESCAPE"
        if not request.requested_tools.issubset(actor.capability.tools):
            return False, "OCS_TOOL_ESCAPE"
        if request.provider_id != actor.provider_id:
            return False, "OCS_PROVIDER_MISMATCH"
        if not request.stop_condition_ref:
            return False, "OCS_STOP_CONDITION_REQUIRED"
        return True, "OK"


def assert_operationalization_invariants() -> None:
    assert len(OCS_RUNTIME_BINDINGS) == 10
    assert set(OCS_RUNTIME_BINDINGS) == set(CANONICAL_OCS_POLICY)
    for key, binding in OCS_RUNTIME_BINDINGS.items():
        policy = CANONICAL_OCS_POLICY[key]
        assert binding.role == policy.role
        assert binding.canonical_policy_id == POLICY_ID
        assert binding.canonical_source_ref == POLICY_SOURCE_REF
        assert binding.production_effects is False
        assert binding.authority_expansion is False
        assert GLOBAL_FORBIDDEN <= binding.forbidden_runtime_capabilities
        assert ("DELEGATE" in binding.allowed_runtime_capabilities) is policy.may_delegate
