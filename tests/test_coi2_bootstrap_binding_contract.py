from __future__ import annotations

from dataclasses import replace

import pytest

from app.cognitive_validation.bootstrap_binding import (
    BootstrapCognitiveBindingError,
    CANONICAL_BRAIN_PATH,
    CANONICAL_COGNITIVE_ENTRYPOINT,
    bind_bootstrap_to_cognition,
)
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus


def binding(**overrides: object) -> InstanceBinding:
    base = InstanceBinding(
        binding_id="binding:test",
        mission_id="mission-001",
        run_id="run:test",
        organization_id="org-001",
        ocs_id="NOESIS",
        profile_version="1",
        profile_hash="profile-hash",
        identity_binding_hash="identity-hash",
        request_hash="request-hash",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="ChatGPT Work",
        capability="reason",
        lease_id="lease-001",
        authority_ref="authority:noesis",
        scope=("mission",),
        state_namespace="state/noesis",
        memory_namespace="memory/noesis",
        generation=7,
        platform_instance_id="platform-001",
        challenge_hash="challenge",
        bootstrap_hash="bootstrap",
        status=InstanceStatus.ACTIVE,
        version=4,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key="idem-001",
        correlation_id="corr-001",
        causation_id=None,
        created_at=1.0,
        updated_at=1.0,
    )
    return replace(base, **overrides)


def test_active_operational_bootstrap_is_bound_to_canonical_cognition() -> None:
    result = bind_bootstrap_to_cognition(binding(), ocs_instance_id="noesis-runtime-001")
    assert result.cognitive_entrypoint == CANONICAL_COGNITIVE_ENTRYPOINT
    assert result.brain_path == CANONICAL_BRAIN_PATH
    assert result.cognitive_path_required is True


def test_bootstrap_binding_preserves_identity_generation_authority_and_namespaces() -> None:
    source = binding()
    result = bind_bootstrap_to_cognition(source, ocs_instance_id="noesis-runtime-001")
    assert result.binding_id == source.binding_id
    assert result.mission_id == source.mission_id
    assert result.ocs_id == source.ocs_id
    assert result.generation == source.generation
    assert result.authority_ref == source.authority_ref
    assert result.state_namespace == source.state_namespace
    assert result.memory_namespace == source.memory_namespace


def test_bootstrap_cognition_never_grants_authority_or_effects() -> None:
    result = bind_bootstrap_to_cognition(binding(), ocs_instance_id="noesis-runtime-001")
    assert result.cognition_grants_authority is False
    assert result.cognition_permits_effects is False


def test_bootstrap_binding_builds_coi1_mission_context() -> None:
    result = bind_bootstrap_to_cognition(binding(), ocs_instance_id="noesis-runtime-001")
    context = result.mission_context(intent="resolve mission", state_revision="state-r42")
    assert context.mission_id == result.mission_id
    assert context.ocs_id == result.ocs_id
    assert context.ocs_instance_id == result.ocs_instance_id
    assert context.generation == result.generation
    assert context.intent == "resolve mission"


def test_non_operational_binding_fails_closed() -> None:
    source = binding(maturity=BindingMaturity.PREPARED_UNVERIFIED)
    with pytest.raises(BootstrapCognitiveBindingError, match="operational_binding"):
        bind_bootstrap_to_cognition(source, ocs_instance_id="runtime-001")


def test_non_active_binding_fails_closed() -> None:
    source = binding(status=InstanceStatus.BOUND)
    with pytest.raises(BootstrapCognitiveBindingError, match="active_instance"):
        bind_bootstrap_to_cognition(source, ocs_instance_id="runtime-001")


def test_missing_instance_id_fails_closed() -> None:
    with pytest.raises(BootstrapCognitiveBindingError, match="instance_id_required"):
        bind_bootstrap_to_cognition(binding(), ocs_instance_id="")


def test_missing_authority_reference_fails_closed() -> None:
    with pytest.raises(BootstrapCognitiveBindingError, match="authority_ref_required"):
        bind_bootstrap_to_cognition(binding(authority_ref=""), ocs_instance_id="runtime-001")


def test_missing_state_or_memory_namespace_fails_closed() -> None:
    for source in (binding(state_namespace=""), binding(memory_namespace="")):
        with pytest.raises(BootstrapCognitiveBindingError, match="namespace_required"):
            bind_bootstrap_to_cognition(source, ocs_instance_id="runtime-001")
