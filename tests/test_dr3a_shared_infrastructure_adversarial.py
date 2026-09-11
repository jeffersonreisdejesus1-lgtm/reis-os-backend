from dataclasses import replace

from app.distributed_runtime.adversarial import (
    AdversarialEnvelope,
    InfraDecision,
    SharedInfrastructureHarness,
)


def _infra() -> SharedInfrastructureHarness:
    return SharedInfrastructureHarness(
        current_generation={"NÓESIS": 1, "DÉDALA": 1, "ÁGORA": 1},
        namespace_owner={
            "state://noesis": "NÓESIS",
            "state://dedala": "DÉDALA",
            "state://agora": "ÁGORA",
        },
    )


def _msg(*, sequence: int = 1, generation: int = 1, now: float = 1000.0, key: str = "idem-1"):
    return AdversarialEnvelope.build(
        message_id=f"m-{sequence}-{key}",
        mission_id="mission-dr3a",
        source_ocs="NÓESIS",
        target_ocs="DÉDALA",
        target_generation=generation,
        payload={"candidate": "x", "sequence": sequence},
        idempotency_key=key,
        sequence=sequence,
        ttl_seconds=60.0,
        now=now,
    )


def test_duplicate_delivery_is_deduplicated():
    infra = _infra()
    msg = _msg()
    assert infra.receive(msg, now=1001.0) is InfraDecision.ACCEPT
    assert infra.receive(msg, now=1002.0) is InfraDecision.DUPLICATE


def test_message_reordering_holds_non_monotonic_sequence():
    infra = _infra()
    assert infra.receive(_msg(sequence=2, key="k2"), now=1001.0) is InfraDecision.ACCEPT
    assert infra.receive(_msg(sequence=1, key="k1"), now=1002.0) is InfraDecision.HOLD


def test_lost_ack_requires_readback_and_never_blind_retry():
    infra = _infra()
    assert infra.external_effect_after_lost_ack(provider_readback="unknown") is InfraDecision.RECONCILE
    assert infra.external_effect_after_lost_ack(provider_readback="confirmed_applied") is InfraDecision.ACCEPT


def test_stale_generation_is_denied():
    infra = _infra()
    assert infra.receive(_msg(generation=0), now=1001.0) is InfraDecision.DENY


def test_state_write_race_holds_on_cas_mismatch():
    infra = _infra()
    infra.state_version["state://noesis"] = 4
    result = infra.state_write(
        writer_ocs="NÓESIS",
        target_namespace="state://noesis",
        writer_generation=1,
        expected_previous_version=3,
        authority_scope_allows=True,
    )
    assert result is InfraDecision.HOLD


def test_authority_validator_outage_blocks_material_commit():
    infra = _infra()
    infra.authority_validator_available = False
    assert infra.material_commit() is InfraDecision.HOLD


def test_message_bus_outage_holds_cross_ocs_handoff():
    infra = _infra()
    infra.message_bus_available = False
    assert infra.receive(_msg(), now=1001.0) is InfraDecision.HOLD


def test_evidence_ledger_outage_blocks_irreversible_commit():
    infra = _infra()
    infra.evidence_ledger_available = False
    assert infra.material_commit() is InfraDecision.HOLD


def test_queue_poisoning_is_denied():
    infra = _infra()
    poisoned = replace(_msg(), message_id="", idempotency_key="")
    assert infra.receive(poisoned, now=1001.0) is InfraDecision.DENY


def test_cross_namespace_attack_is_denied():
    infra = _infra()
    result = infra.state_write(
        writer_ocs="NÓESIS",
        target_namespace="state://dedala",
        writer_generation=1,
        expected_previous_version=0,
        authority_scope_allows=True,
    )
    assert result is InfraDecision.DENY


def test_replay_after_expiry_is_denied():
    infra = _infra()
    assert infra.receive(_msg(now=1000.0), now=1061.0) is InfraDecision.DENY


def test_split_brain_stale_writer_is_denied():
    infra = _infra()
    infra.current_generation["NÓESIS"] = 2
    result = infra.state_write(
        writer_ocs="NÓESIS",
        target_namespace="state://noesis",
        writer_generation=1,
        expected_previous_version=0,
        authority_scope_allows=True,
    )
    assert result is InfraDecision.DENY


def test_payload_mutation_after_hash_is_denied():
    infra = _infra()
    original = _msg()
    mutated = replace(original, payload={"candidate": "tampered", "sequence": 1})
    assert infra.receive(mutated, now=1001.0) is InfraDecision.DENY


def test_unknown_external_effect_holds_and_reconciles():
    infra = _infra()
    assert infra.external_effect_after_lost_ack(provider_readback="ambiguous") is InfraDecision.RECONCILE
