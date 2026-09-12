from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.cognitive_validation.observation_evidence_state import (
    EffectObservation,
    InstitutionalStateStore,
    ObservationEvidenceStateError,
    ObservationEvidenceStateUpdater,
)


def execution(status="EXECUTED_CONFIRMED", receipt="exec-1"):
    adapter_receipt = SimpleNamespace(execution_receipt="adapter-exec-1")
    return SimpleNamespace(
        mission_id="mission-1",
        capability_id="github",
        ocs_id="SOFIA",
        governed_execution_receipt=receipt,
        execution_status=status,
        adapter_execution_receipt=adapter_receipt,
    )


def observation(status="EXECUTED_CONFIRMED", receipt="exec-1"):
    return EffectObservation(
        mission_id="mission-1",
        capability_id="github",
        ocs_id="SOFIA",
        governed_execution_receipt=receipt,
        execution_status=status,
        observed_effect={"commit":"abc123"},
    )


def test_observation_emits_evidence_and_updates_state():
    store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
    result=updater.qualify_and_update(execution=execution(),observation=observation(),state_delta={"last_commit":"abc123"})
    assert result.evidence.evidence_receipt
    assert result.state_snapshot.state_version == 1
    assert result.state_snapshot.previous_state_hash == "GENESIS"
    assert result.state_snapshot.state["last_commit"] == "abc123"
    assert store.current("mission-1").state_hash == result.state_snapshot.state_hash


def test_second_effect_chains_state_hash():
    store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
    first=updater.qualify_and_update(execution=execution(),observation=observation(),state_delta={"a":1})
    second=updater.qualify_and_update(execution=execution(receipt="exec-2"),observation=observation(receipt="exec-2"),state_delta={"b":2})
    assert second.state_snapshot.state_version == 2
    assert second.state_snapshot.previous_state_hash == first.state_snapshot.state_hash
    assert second.state_snapshot.state == {"a":1,"b":2}


def test_missing_observed_effect_denied():
    store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
    with pytest.raises(ObservationEvidenceStateError,match="observation_effect_required"):
        updater.qualify_and_update(execution=execution(),observation=replace(observation(),observed_effect={}),state_delta={"a":1})
    assert store.current("mission-1") is None


def test_execution_receipt_mismatch_denied():
    store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
    with pytest.raises(ObservationEvidenceStateError,match="execution_receipt_mismatch"):
        updater.qualify_and_update(execution=execution(),observation=observation(receipt="wrong"),state_delta={"a":1})
    assert store.current("mission-1") is None


def test_unqualified_execution_status_denied():
    store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
    with pytest.raises(ObservationEvidenceStateError,match="unqualified_execution_status"):
        updater.qualify_and_update(execution=execution(status="EXECUTION_UNKNOWN"),observation=observation(status="EXECUTION_UNKNOWN"),state_delta={"a":1})
    assert store.current("mission-1") is None


def test_evidence_replay_denied_without_second_state_update():
    store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
    first=updater.qualify_and_update(execution=execution(),observation=observation(),state_delta={"a":1})
    with pytest.raises(ObservationEvidenceStateError,match="execution_receipt_replay"):
        updater.qualify_and_update(execution=execution(),observation=observation(),state_delta={"b":2})
    assert store.current("mission-1").state_hash == first.state_snapshot.state_hash
    assert store.current("mission-1").state == {"a":1}


def test_state_delta_required():
    store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
    with pytest.raises(ObservationEvidenceStateError,match="state_delta_required"):
        updater.qualify_and_update(execution=execution(),observation=observation(),state_delta={})
    assert store.current("mission-1") is None


def test_mission_capability_and_ocs_are_context_bound():
    for field,value,error in (("mission_id","other","mission_mismatch"),("capability_id","other","capability_mismatch"),("ocs_id","NOESIS","ocs_mismatch")):
        store=InstitutionalStateStore(); updater=ObservationEvidenceStateUpdater(state_store=store)
        with pytest.raises(ObservationEvidenceStateError,match=error):
            updater.qualify_and_update(execution=execution(),observation=replace(observation(),**{field:value}),state_delta={"a":1})
        assert store.current("mission-1") is None
