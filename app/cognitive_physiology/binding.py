from __future__ import annotations

from dataclasses import dataclass

from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceStatus,
)
from app.profile_bindings.profiles import get_profile

from .runtime import CognitivePhysiologyRuntime


@dataclass(frozen=True)
class CognitiveBindingContext:
    binding_id: str
    authority_ref: str
    profile_hash: str
    generation: int
    runtime: CognitivePhysiologyRuntime


def bind_cognitive_runtime(
    binding: InstanceBinding,
) -> CognitiveBindingContext:
    """Derive cognition from an institutional binding without granting authority."""
    if binding.maturity is not BindingMaturity.OPERATIONALLY_BOUND_L1:
        raise PermissionError("cognitive_runtime_requires_operational_binding")
    if binding.status is not InstanceStatus.ACTIVE:
        raise PermissionError("cognitive_runtime_requires_active_instance")
    if binding.generation < 0:
        raise ValueError("binding_generation_must_be_non_negative")
    if not binding.authority_ref:
        raise PermissionError("binding_authority_reference_required")

    profile = get_profile(binding.ocs_id)
    if binding.profile_version != profile.version:
        raise PermissionError("binding_profile_version_mismatch")
    if binding.state_namespace != profile.state_namespace:
        raise PermissionError("binding_state_namespace_mismatch")
    if binding.memory_namespace != profile.memory_namespace:
        raise PermissionError("binding_memory_namespace_mismatch")

    runtime = CognitivePhysiologyRuntime(
        ocs_id=binding.ocs_id,
        identity_ref=profile.identity,
        state_namespace=binding.state_namespace,
        memory_namespace=binding.memory_namespace,
        generation=binding.generation,
    )
    return CognitiveBindingContext(
        binding_id=binding.binding_id,
        authority_ref=binding.authority_ref,
        profile_hash=binding.profile_hash,
        generation=binding.generation,
        runtime=runtime,
    )
