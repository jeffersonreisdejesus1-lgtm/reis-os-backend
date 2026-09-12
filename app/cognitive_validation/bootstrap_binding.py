from __future__ import annotations

from dataclasses import dataclass

from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceStatus,
)

from .universal_entrypoint import CognitiveMissionContext


CANONICAL_COGNITIVE_ENTRYPOINT = "UNIVERSAL_COGNITIVE_ENTRYPOINT"
CANONICAL_BRAIN_PATH = "AB0-AB13/canonical"


class BootstrapCognitiveBindingError(RuntimeError):
    """Fail-closed error for invalid COI2 bootstrap cognitive bindings."""


@dataclass(frozen=True, slots=True)
class BootstrapCognitiveBinding:
    binding_id: str
    mission_id: str
    ocs_id: str
    ocs_instance_id: str
    generation: int
    cognitive_entrypoint: str
    brain_path: str
    authority_ref: str
    state_namespace: str
    memory_namespace: str
    cognitive_path_required: bool = True
    cognition_grants_authority: bool = False
    cognition_permits_effects: bool = False

    def mission_context(self, *, intent: str, state_revision: str | None = None) -> CognitiveMissionContext:
        return CognitiveMissionContext(
            mission_id=self.mission_id,
            ocs_id=self.ocs_id,
            ocs_instance_id=self.ocs_instance_id,
            generation=self.generation,
            intent=intent,
            state_revision=state_revision,
        )


def bind_bootstrap_to_cognition(
    binding: InstanceBinding,
    *,
    ocs_instance_id: str,
) -> BootstrapCognitiveBinding:
    """Derive the mandatory cognitive route from an active institutional binding.

    COI2 binds bootstrap identity/state/authority context to the COI1 canonical
    cognitive ingress. It does not issue cognitive receipts or action authority.
    """
    if binding.maturity is not BindingMaturity.OPERATIONALLY_BOUND_L1:
        raise BootstrapCognitiveBindingError("bootstrap_cognition_requires_operational_binding")
    if binding.status is not InstanceStatus.ACTIVE:
        raise BootstrapCognitiveBindingError("bootstrap_cognition_requires_active_instance")
    if not ocs_instance_id.strip():
        raise BootstrapCognitiveBindingError("bootstrap_cognition_instance_id_required")
    if binding.generation < 0:
        raise BootstrapCognitiveBindingError("bootstrap_cognition_generation_invalid")
    if not binding.authority_ref:
        raise BootstrapCognitiveBindingError("bootstrap_cognition_authority_ref_required")
    if not binding.state_namespace or not binding.memory_namespace:
        raise BootstrapCognitiveBindingError("bootstrap_cognition_namespace_required")

    return BootstrapCognitiveBinding(
        binding_id=binding.binding_id,
        mission_id=binding.mission_id,
        ocs_id=binding.ocs_id,
        ocs_instance_id=ocs_instance_id,
        generation=binding.generation,
        cognitive_entrypoint=CANONICAL_COGNITIVE_ENTRYPOINT,
        brain_path=CANONICAL_BRAIN_PATH,
        authority_ref=binding.authority_ref,
        state_namespace=binding.state_namespace,
        memory_namespace=binding.memory_namespace,
        cognitive_path_required=True,
        cognition_grants_authority=False,
        cognition_permits_effects=False,
    )
