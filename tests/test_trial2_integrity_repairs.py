from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, update

from app.single_surface_trial.trial2_integrity import IntegrityCheckedTrial2Store
from app.single_surface_trial.trial2_store import Trial2Hold, handoffs, missions


def valid_authority(authority_ref: str, actor: str, role: str) -> bool:
    return bool(authority_ref and actor and role)


def _store(tmp_path: Path, name: str) -> IntegrityCheckedTrial2Store:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / name}")
    store = IntegrityCheckedTrial2Store(engine)
    store.create_schema()
    return store


def _mission_with_active_dedala(
    store: IntegrityCheckedTrial2Store, mission_id: str
) -> dict[str, object]:
    store.create_mission(
        mission_id,
        canonical_state_ref="canon:v1",
        current_gate="TRIAL_2",
        autonomy_budget=8,
    )
    return store.bind(
        mission_id,
        "DÉDALA",
        "i-d",
        authority_ref="auth:d",
        role="architect",
        activate_if_empty=True,
    )


def test_f1_idempotency_payload_mismatch_holds_without_mutation(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, "f1.sqlite")
    binding = _mission_with_active_dedala(store, "m-f1")

    first = store.apply_synthetic_effect(
        "m-f1",
        ocs_id="DÉDALA",
        instance_id="i-d",
        epoch=int(binding["epoch"]),
        authority_ref="auth:d",
        idempotency_key="same-key",
        payload={"value": 1},
    )
    assert first.mutation_count == 1
    assert store.effect_count("m-f1") == 1

    with pytest.raises(Trial2Hold, match="idempotency_key_payload_mismatch"):
        store.apply_synthetic_effect(
            "m-f1",
            ocs_id="DÉDALA",
            instance_id="i-d",
            epoch=int(binding["epoch"]),
            authority_ref="auth:d",
            idempotency_key="same-key",
            payload={"value": 2},
        )

    assert store.effect_count("m-f1") == 1


def test_f2_tampered_handoff_envelope_holds_before_actor_switch(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, "f2-accept.sqlite")
    _mission_with_active_dedala(store, "m-f2a")
    store.bind(
        "m-f2a",
        "SOFIA",
        "i-s",
        authority_ref="auth:s",
        role="planner",
    )
    store.checkpoint("m-f2a", instance_id="i-d", local_state={"phase": "ready"})
    handoff_id = store.issue_handoff(
        "m-f2a",
        route_id="L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001",
        target_instance_id="i-s",
        target_ocs_id="SOFIA",
        envelope={"next": "SOFIA"},
    )

    with store._engine.begin() as conn:
        conn.execute(
            update(handoffs)
            .where(handoffs.c.handoff_id == handoff_id)
            .values(envelope_json='{"next":"TAMPERED"}')
        )

    with pytest.raises(Trial2Hold, match="handoff_envelope_integrity_failure"):
        store.accept_handoff("m-f2a", handoff_id)

    with store._engine.connect() as conn:
        mission = conn.execute(
            select(missions).where(missions.c.mission_id == "m-f2a")
        ).mappings().one()
        handoff = conn.execute(
            select(handoffs).where(handoffs.c.handoff_id == handoff_id)
        ).mappings().one()
    assert mission["active_ocs_id"] == "DÉDALA"
    assert mission["active_instance_id"] == "i-d"
    assert handoff["accepted"] is False
    assert handoff["acceptance_receipt_ref"] is None


def test_f2_tampered_handoff_envelope_holds_during_restart_recovery(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, "f2-recovery.sqlite")
    _mission_with_active_dedala(store, "m-f2r")
    store.bind(
        "m-f2r",
        "SOFIA",
        "i-s",
        authority_ref="auth:s",
        role="planner",
    )
    store.checkpoint("m-f2r", instance_id="i-d", local_state={"phase": "ready"})
    handoff_id = store.issue_handoff(
        "m-f2r",
        route_id="L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001",
        target_instance_id="i-s",
        target_ocs_id="SOFIA",
        envelope={"next": "SOFIA"},
    )
    store.accept_handoff("m-f2r", handoff_id)
    store.checkpoint("m-f2r", instance_id="i-s", local_state={"phase": "planned"})

    with store._engine.begin() as conn:
        conn.execute(
            update(handoffs)
            .where(handoffs.c.handoff_id == handoff_id)
            .values(envelope_json='{"next":"TAMPERED_AFTER_ACCEPT"}')
        )

    with pytest.raises(Trial2Hold, match="handoff_envelope_integrity_failure"):
        store.recover_snapshot("m-f2r", authority_validator=valid_authority)
