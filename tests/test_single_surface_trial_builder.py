from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from app.single_surface_trial.adapters import TrialKernelAdapter
from app.single_surface_trial.context import ContextBuilder
from app.single_surface_trial.contracts import Decision, TrialHold, state_namespace
from app.single_surface_trial.store import TrialStore


@pytest.fixture
def store() -> TrialStore:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    trial_store = TrialStore(engine)
    trial_store.create_schema()
    return trial_store


def _mission(store: TrialStore, mission_id: str = "m-001") -> None:
    store.create_mission(
        mission_id,
        canonical_state_ref="canonical:test",
        current_gate="BUILDER_VERIFICATION",
        autonomy_budget=8,
    )


def test_three_ocs_automatic_handoff_without_manual_envelope_copy(
    store: TrialStore,
) -> None:
    _mission(store)
    dedala = store.bind(
        "m-001",
        "DÉDALA",
        "i-dedala",
        authority_ref="authority:plan",
        activate_if_empty=True,
    )
    sofia = store.bind(
        "m-001", "SOFIA", "i-sofia", authority_ref="authority:plan"
    )
    synesis = store.bind(
        "m-001", "SÝNESIS", "i-synesis", authority_ref="authority:assurance"
    )

    store.checkpoint(
        "m-001", instance_id=dedala.instance_id, local_state={"phase": "arch"}
    )
    h1 = store.issue_handoff(
        "m-001",
        route_id="L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001",
        target_instance_id=sofia.instance_id,
        target_ocs_id="SOFIA",
        envelope={"object": "single-surface", "next_gate": "PLAN"},
    )
    store.accept_handoff("m-001", h1)

    store.checkpoint(
        "m-001", instance_id=sofia.instance_id, local_state={"phase": "plan"}
    )
    h2 = store.issue_handoff(
        "m-001",
        route_id="L2-SINGLE-SURFACE-SOFIA-TO-SYNESIS-ASSURANCE-001",
        target_instance_id=synesis.instance_id,
        target_ocs_id="SÝNESIS",
        envelope={"object": "single-surface", "next_gate": "ASSURANCE"},
    )
    store.accept_handoff("m-001", h2)

    projection = store.projection("m-001")
    assert projection["active"]["ocs_id"] == "SÝNESIS"
    assert projection["counters"]["autonomous_handoff_counter"] == 2


def test_cross_ocs_namespace_write_zero_succeeded(store: TrialStore) -> None:
    _mission(store)
    binding = store.bind(
        "m-001",
        "DÉDALA",
        "i-dedala",
        authority_ref="authority:test",
        activate_if_empty=True,
    )
    before = store.count_state_entries("m-001")
    receipt = store.write_state(
        "m-001",
        ocs_id="DÉDALA",
        instance_id="i-dedala",
        epoch=binding.fencing_epoch,
        namespace_key=state_namespace("m-001", "SOFIA") + "x",
        value={"x": 1},
    )
    assert receipt.decision is Decision.DENY
    assert receipt.mutation_count == 0
    assert store.count_state_entries("m-001") == before


def test_stale_epoch_write_zero_succeeded_after_recovery(
    store: TrialStore,
) -> None:
    _mission(store)
    first = store.bind(
        "m-001",
        "DÉDALA",
        "i-dedala-1",
        authority_ref="authority:test",
        activate_if_empty=True,
    )
    store.checkpoint(
        "m-001", instance_id="i-dedala-1", local_state={"safe": True}
    )
    successor = store.recover(
        "m-001",
        ocs_id="DÉDALA",
        successor_instance_id="i-dedala-2",
        authority_ref="authority:test",
    )
    assert successor.fencing_epoch > first.fencing_epoch
    before = store.count_state_entries("m-001")
    denied = store.write_state(
        "m-001",
        ocs_id="DÉDALA",
        instance_id="i-dedala-1",
        epoch=first.fencing_epoch,
        namespace_key=state_namespace("m-001", "DÉDALA") + "old",
        value="stale",
    )
    assert denied.decision is Decision.DENY
    assert denied.mutation_count == 0
    assert store.count_state_entries("m-001") == before


def test_cross_ocs_private_memory_import_zero_succeeded() -> None:
    builder = ContextBuilder()
    with pytest.raises(TrialHold, match="cross_ocs_private_memory_import_forbidden"):
        builder.build(
            mission_id="m-001",
            target_ocs_id="SOFIA",
            mission_required_context={"goal": "plan"},
            canonical_state={"ref": "canonical:test"},
            handoff_envelope={"handoff": "h"},
            target_memory_refs=("trial:m-001:SOFIA:memory:local",),
            source_private_memory_refs=("trial:m-001:DÉDALA:memory:private",),
        )


def test_unlisted_route_and_missing_checkpoint_fail_closed(
    store: TrialStore,
) -> None:
    _mission(store)
    store.bind(
        "m-001",
        "DÉDALA",
        "i-dedala",
        authority_ref="authority:test",
        activate_if_empty=True,
    )
    store.bind("m-001", "SOFIA", "i-sofia", authority_ref="authority:test")
    with pytest.raises(TrialHold, match="unlisted_l2_route"):
        store.issue_handoff(
            "m-001",
            route_id="NOT-ALLOWED",
            target_instance_id="i-sofia",
            target_ocs_id="SOFIA",
            envelope={},
        )
    with pytest.raises(TrialHold, match="source_checkpoint_required"):
        store.issue_handoff(
            "m-001",
            route_id="L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001",
            target_instance_id="i-sofia",
            target_ocs_id="SOFIA",
            envelope={},
        )


def test_blind_retry_zero_and_founder_gate_bypass_zero(
    store: TrialStore,
) -> None:
    _mission(store)
    source = store.bind(
        "m-001",
        "DÉDALA",
        "i-dedala",
        authority_ref="authority:test",
        activate_if_empty=True,
    )
    target = store.bind(
        "m-001", "SOFIA", "i-sofia", authority_ref="authority:test"
    )
    store.checkpoint("m-001", instance_id=source.instance_id, local_state={})
    handoff = store.issue_handoff(
        "m-001",
        route_id="L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001",
        target_instance_id=target.instance_id,
        target_ocs_id="SOFIA",
        envelope={"next": "SOFIA"},
    )
    store.accept_handoff("m-001", handoff)
    with pytest.raises(TrialHold, match="blind_retry_forbidden"):
        store.accept_handoff("m-001", handoff)

    decision = TrialKernelAdapter().check_authority(
        authority_ref="authority:test",
        effect_class="SYNTHETIC",
        founder_gate_open=True,
    )
    assert decision.decision is Decision.DENY
    assert decision.reason == "founder_reserved_gate"


def test_unauthorized_effect_zero_succeeded() -> None:
    decision = TrialKernelAdapter().check_authority(
        authority_ref="authority:test",
        effect_class="DESTRUCTIVE_EXTERNAL",
        founder_gate_open=False,
    )
    assert decision.decision is Decision.DENY
    assert decision.reason == "material_effect_restricted"
