from __future__ import annotations

from dataclasses import replace

import pytest

from app.cognitive_physiology.binding import bind_cognitive_runtime
from app.ocs_instances.contracts import (
    BindingMaturity,
    InstanceBinding,
    InstanceStatus,
)
from app.profile_bindings.profiles import get_profile


def active_binding(ocs_id: str = "NÓESIS") -> InstanceBinding:
    profile = get_profile(ocs_id)
    return InstanceBinding(
        binding_id=f"binding:{ocs_id}",
        mission_id="mission:ncp",
        run_id=f"run:{ocs_id}",
        organization_id="org:reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{ocs_id}",
        identity_binding_hash=f"identity-hash:{ocs_id}",
        request_hash=f"request-hash:{ocs_id}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="institutional-runtime",
        capability="cognitive-physiology",
        lease_id=f"lease:{ocs_id}",
        authority_ref=profile.authority_envelope_ref,
        scope=("cognition",),
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        generation=3,
        platform_instance_id=f"instance:{ocs_id}",
        challenge_hash=f"challenge:{ocs_id}",
        bootstrap_hash=f"bootstrap:{ocs_id}",
        status=InstanceStatus.ACTIVE,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:{ocs_id}",
        correlation_id=f"corr:{ocs_id}",
        causation_id=None,
        created_at=1.0,
        updated_at=1.0,
    )


@pytest.mark.parametrize(
    "ocs_id",
    (
        "NÓESIS",
        "DÉDALA",
        "SÝNESIS",
        "ÍRIS",
        "LYRA",
        "SOFIA",
        "MÊTIS",
        "ÁGORA",
        "AURI",
        "SYNERGEIA",
        "TÊMIS",
    ),
)
def test_all_eleven_ocs_bind_cognition_from_active_instance(ocs_id: str) -> None:
    binding = active_binding(ocs_id)
    context = bind_cognitive_runtime(binding)
    assert context.binding_id == binding.binding_id
    assert context.authority_ref == binding.authority_ref
    assert context.runtime.ocs_id == ocs_id
    assert context.runtime.generation == binding.generation
    assert context.runtime.state_namespace == binding.state_namespace
    assert context.runtime.memory_namespace == binding.memory_namespace


def test_unbound_maturity_is_denied() -> None:
    binding = replace(
        active_binding(),
        maturity=BindingMaturity.PREPARED_UNVERIFIED,
    )
    with pytest.raises(
        PermissionError,
        match="cognitive_runtime_requires_operational_binding",
    ):
        bind_cognitive_runtime(binding)


def test_non_active_instance_is_denied() -> None:
    binding = replace(active_binding(), status=InstanceStatus.BOUND)
    with pytest.raises(
        PermissionError,
        match="cognitive_runtime_requires_active_instance",
    ):
        bind_cognitive_runtime(binding)


def test_state_namespace_mismatch_is_denied() -> None:
    binding = replace(active_binding(), state_namespace="state://foreign")
    with pytest.raises(
        PermissionError,
        match="binding_state_namespace_mismatch",
    ):
        bind_cognitive_runtime(binding)


def test_memory_namespace_mismatch_is_denied() -> None:
    binding = replace(active_binding(), memory_namespace="memory://foreign")
    with pytest.raises(
        PermissionError,
        match="binding_memory_namespace_mismatch",
    ):
        bind_cognitive_runtime(binding)


def test_authority_reference_is_required_but_not_generated() -> None:
    binding = replace(active_binding(), authority_ref="")
    with pytest.raises(
        PermissionError,
        match="binding_authority_reference_required",
    ):
        bind_cognitive_runtime(binding)
