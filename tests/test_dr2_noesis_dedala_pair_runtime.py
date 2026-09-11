from __future__ import annotations

import os

import pytest

from app.distributed_runtime.pair import NoesisDedalaPairRuntime, PairMessage
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import get_profile


def active_binding(ocs_id: str, generation: int = 11) -> InstanceBinding:
    profile = get_profile(ocs_id)
    slug = "noesis" if ocs_id == "NÓESIS" else "dedala"
    return InstanceBinding(
        binding_id=f"binding:dr2:{slug}:g{generation}",
        mission_id="mission:dr2-pair-runtime",
        run_id=f"run:dr2:{slug}",
        organization_id="org:reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-hash:{slug}",
        request_hash=f"request-hash:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr2-local-process",
        capability="cognitive-physiology",
        lease_id=f"lease:dr2:{slug}",
        authority_ref=profile.authority_envelope_ref,
        scope=("cognition", "runtime-health", "governed-handoff"),
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        generation=generation,
        platform_instance_id=None,
        challenge_hash=f"challenge:dr2:{slug}",
        bootstrap_hash=f"bootstrap:dr2:{slug}",
        status=InstanceStatus.ACTIVE,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:dr2:{slug}",
        correlation_id="corr:dr2-pair",
        causation_id=None,
        created_at=1.0,
        updated_at=1.0,
    )


def pair_runtime() -> NoesisDedalaPairRuntime:
    return NoesisDedalaPairRuntime(active_binding("NÓESIS"), active_binding("DÉDALA"))


def test_dr2_pair_has_distinct_material_execution_contexts_and_namespaces() -> None:
    pair = pair_runtime()
    started = pair.start()
    try:
        noesis = started["NÓESIS"]
        dedala = started["DÉDALA"]
        assert noesis.pid != os.getpid()
        assert dedala.pid != os.getpid()
        assert noesis.pid != dedala.pid
        assert noesis.execution_context_id != dedala.execution_context_id
        assert noesis.failure_domain_id != dedala.failure_domain_id
        assert noesis.instance_id != dedala.instance_id
        assert noesis.state_namespace != dedala.state_namespace
        assert noesis.memory_namespace != dedala.memory_namespace
        assert noesis.authority_ref != dedala.authority_ref
    finally:
        pair.stop_all()


def test_dr2_governed_handoff_is_causal_and_hash_bound() -> None:
    pair = pair_runtime()
    pair.start()
    try:
        receipt = pair.handoff(
            source_ocs="NÓESIS",
            target_ocs="DÉDALA",
            payload={"request": "architectural-review", "artifact": "dr2"},
            causation_id="cause:dr2:noesis-to-dedala",
        )
        assert receipt.accepted is True
        assert receipt.source_ocs == "NÓESIS"
        assert receipt.target_ocs == "DÉDALA"
        assert receipt.payload_hash
        assert receipt.monotonic_sequence >= 3
    finally:
        pair.stop_all()


def test_dr2_independent_restart_preserves_peer_and_advances_generation() -> None:
    pair = pair_runtime()
    started = pair.start()
    old_dedala = started["DÉDALA"]
    try:
        replacement = pair.restart("DÉDALA")
        noesis_health = pair.health("NÓESIS")
        assert replacement.instance_id != old_dedala.instance_id
        assert replacement.pid != old_dedala.pid
        assert replacement.generation == old_dedala.generation + 1
        assert noesis_health.instance_id == started["NÓESIS"].instance_id
        assert noesis_health.generation == started["NÓESIS"].generation
    finally:
        pair.stop_all()


def test_dr2_stale_target_generation_is_rejected_after_restart() -> None:
    pair = pair_runtime()
    started = pair.start()
    try:
        stale = PairMessage.build(
            mission_id="mission:dr2-stale",
            source=started["NÓESIS"],
            target=started["DÉDALA"],
            payload={"request": "stale-delivery"},
            causation_id="cause:stale",
        )
        pair.restart("DÉDALA")
        with pytest.raises(RuntimeError, match="stale_target_generation"):
            pair._workers["DÉDALA"].accept_handoff(stale)
    finally:
        pair.stop_all()


def test_dr2_route_cannot_target_same_ocs() -> None:
    pair = pair_runtime()
    pair.start()
    try:
        with pytest.raises(PermissionError, match="pair_handoff_route_denied"):
            pair.handoff(
                source_ocs="NÓESIS",
                target_ocs="NÓESIS",
                payload={"forbidden": True},
                causation_id="cause:self-route",
            )
    finally:
        pair.stop_all()


def test_dr2_requires_exactly_noesis_and_dedala() -> None:
    with pytest.raises(PermissionError, match="dr2_requires_noesis_and_dedala"):
        NoesisDedalaPairRuntime(active_binding("NÓESIS"), active_binding("NÓESIS"))
