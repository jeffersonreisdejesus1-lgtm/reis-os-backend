import time

import pytest

from app.distributed_runtime.causal_mission import (
    CausalMissionEnvelope,
    CausalMissionWorker,
    _hash_payload,
)
from app.ocs_instances.contracts import BindingMaturity, InstanceBinding, InstanceStatus
from app.profile_bindings.profiles import PROFILES


def _binding(ocs_id: str, generation: int = 1) -> InstanceBinding:
    profile = PROFILES[ocs_id]
    now = time.time()
    slug = ocs_id.casefold()
    return InstanceBinding(
        binding_id=f"binding:{slug}:dr5a-fencing",
        mission_id="mission:dr5a-forced-11ocs",
        run_id=f"run:{slug}:dr5a-fencing",
        organization_id="reis-os",
        ocs_id=ocs_id,
        profile_version=profile.version,
        profile_hash=f"profile-hash:{slug}",
        identity_binding_hash=f"identity-binding:{slug}",
        request_hash=f"request:{slug}",
        maturity=BindingMaturity.OPERATIONALLY_BOUND_L1,
        host="dr5a-provider-independent",
        capability="cognitive-runtime",
        lease_id=f"lease:{slug}:dr5a",
        authority_ref=profile.authority_envelope_ref,
        scope=("cognition", "handoff", "evidence"),
        state_namespace=profile.state_namespace,
        memory_namespace=profile.memory_namespace,
        generation=generation,
        platform_instance_id=None,
        challenge_hash=f"challenge:{slug}",
        bootstrap_hash=f"bootstrap:{slug}",
        status=InstanceStatus.ACTIVE,
        version=1,
        predecessor_binding_id=None,
        checkpoint_version=0,
        checkpoint_hash=None,
        hazel_event_hash=None,
        idempotency_key=f"idem:{slug}:dr5a-fencing",
        correlation_id="corr:dr5a-fencing",
        causation_id=None,
        created_at=now,
        updated_at=now,
    )


def _envelope(*, target_ocs: str, generation: int, payload: dict, payload_hash: str | None = None):
    digest = _hash_payload(payload) if payload_hash is None else payload_hash
    return CausalMissionEnvelope(
        message_id="dr5a-msg:fencing-test",
        mission_id="mission:dr5a-forced-11ocs",
        source_ocs="NÓESIS",
        source_instance_id="source-instance",
        source_generation=1,
        target_ocs=target_ocs,
        target_expected_generation=generation,
        payload=payload,
        payload_hash=digest,
        predecessor_output_hash=digest,
        causation_id="dr5a-msg:previous",
        correlation_id="dr5a-correlation:fencing",
        trace_id="dr5a-trace:fencing",
    )


def test_dr5a_materially_rejects_stale_target_generation():
    worker = CausalMissionWorker(_binding("DÉDALA", generation=1), "dr5a-dedala-fencing")
    try:
        worker.start()
        envelope = _envelope(
            target_ocs="DÉDALA",
            generation=0,
            payload={"goal": "stale generation", "contributions": {}},
        )
        with pytest.raises(RuntimeError, match="dr5a_stale_generation"):
            worker.process(envelope)
    finally:
        worker.crash()


def test_dr5a_materially_rejects_payload_mutation_after_hash():
    worker = CausalMissionWorker(_binding("ÁGORA", generation=1), "dr5a-agora-integrity")
    try:
        worker.start()
        original = {"goal": "original", "contributions": {}}
        mutated = {"goal": "mutated", "contributions": {}}
        envelope = _envelope(
            target_ocs="ÁGORA",
            generation=1,
            payload=mutated,
            payload_hash=_hash_payload(original),
        )
        with pytest.raises(RuntimeError, match="dr5a_payload_hash_mismatch"):
            worker.process(envelope)
    finally:
        worker.crash()
