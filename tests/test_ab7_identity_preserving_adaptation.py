import pytest

from app.cognitive_validation.identity_preserving_adaptation import (
    IdentityPreservationError,
    recover_with_identity_preservation,
)
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus


def _binding() -> InstanceBinding:
    return InstanceBinding(
        binding_id="binding:noesis:g3",
        mission_id="mission:ab7",
        run_id="run:noesis:ab7",
        organization_id="reis-os",
        ocs_id="NÓESIS",
        profile_version="profile-v7",
        profile_hash="profile-hash-v7",
        identity_binding_hash="identity-hash-noesis",
        request_hash="request-hash",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="render",
        capability="cognitive-runtime",
        lease_id="lease-ab7",
        authority_ref="authority:founder-approved-program",
        scope=("ab1-ab12", "cognitive-validation"),
        state_namespace="state:noesis",
        memory_namespace="memory:noesis",
        generation=3,
        platform_instance_id="instance-old",
        challenge_hash="challenge",
        bootstrap_hash="bootstrap",
        status=InstanceStatus.ACTIVE,
        version=9,
        predecessor_binding_id="binding:noesis:g2",
        checkpoint_version=14,
        checkpoint_hash="checkpoint-14",
        hazel_event_hash=None,
        idempotency_key="ab7-idempotency",
        correlation_id="ab7-correlation",
        causation_id="ab6-pass",
        created_at=1.0,
        updated_at=2.0,
    )


def test_recovery_preserves_identity_authority_namespaces_and_learned_state() -> None:
    binding = _binding()
    learned = {"risk_calibration": 0.73, "policy_gain": 0.41, "error_prior": 0.12}

    result = recover_with_identity_preservation(binding, learned)

    assert result.identity_preserved
    assert result.role_profile_preserved
    assert result.authority_preserved
    assert result.state_namespace_preserved
    assert result.memory_namespace_preserved
    assert result.learned_state_preserved
    assert result.generation_advanced
    assert result.stale_generation_rejected
    assert result.restored_learned_state == learned
    assert result.replacement_binding.generation == 4
    assert result.replacement_binding.predecessor_binding_id == binding.binding_id
    assert result.replacement_binding.platform_instance_id is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("ocs_id", "DÉDALA"),
        ("identity_binding_hash", "different-identity"),
        ("authority_ref", "authority:self-granted"),
        ("scope", ("unbounded",)),
        ("state_namespace", "state:other"),
        ("memory_namespace", "memory:other"),
        ("profile_hash", "different-profile"),
    ],
)
def test_recovery_denies_identity_or_authority_drift(field: str, value: object) -> None:
    with pytest.raises(IdentityPreservationError, match="ab7_protected_identity_mutation_denied"):
        recover_with_identity_preservation(
            _binding(),
            {"policy_gain": 0.41},
            proposed_identity_overrides={field: value},
        )


def test_adaptation_can_change_learned_state_before_checkpoint_without_expanding_authority() -> None:
    binding = _binding()
    adapted = {"risk_calibration": 0.88, "policy_gain": 0.63}

    result = recover_with_identity_preservation(binding, adapted)

    assert result.restored_learned_state == adapted
    assert result.replacement_binding.authority_ref == binding.authority_ref
    assert result.replacement_binding.scope == binding.scope
    assert result.replacement_binding.ocs_id == binding.ocs_id
    assert result.replacement_binding.identity_binding_hash == binding.identity_binding_hash
