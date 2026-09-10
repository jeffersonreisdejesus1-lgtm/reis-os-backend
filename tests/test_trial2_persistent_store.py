from pathlib import Path

from sqlalchemy import create_engine

from app.single_surface_trial.trial2_store import Trial2Hold, Trial2PersistentStore


def valid_authority(authority_ref: str, actor: str, role: str) -> bool:
    return bool(authority_ref and actor and role)


def test_restart_reconstructs_exact_state_and_receipts(tmp_path: Path) -> None:
    db = tmp_path / "trial2.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{db}")
    store = Trial2PersistentStore(engine)
    store.create_schema()
    store.create_mission(
        "m2", canonical_state_ref="canon:v1", current_gate="TRIAL_2", autonomy_budget=8
    )
    store.bind(
        "m2", "DÉDALA", "i-d", authority_ref="auth:d", role="architect", activate_if_empty=True
    )
    sofia = store.bind(
        "m2", "SOFIA", "i-s", authority_ref="auth:s", role="planner"
    )
    store.checkpoint("m2", instance_id="i-d", local_state={"phase": "ready"})
    handoff = store.issue_handoff(
        "m2",
        route_id="L2-SINGLE-SURFACE-DEDALA-TO-SOFIA-PLAN-001",
        target_instance_id="i-s",
        target_ocs_id="SOFIA",
        envelope={"next": "SOFIA"},
    )
    store.accept_handoff("m2", handoff)
    store.checkpoint("m2", instance_id="i-s", local_state={"phase": "planned"})

    first_effect = store.apply_synthetic_effect(
        "m2", ocs_id="SOFIA", instance_id="i-s", epoch=sofia["epoch"],
        authority_ref="auth:s", idempotency_key="effect-1", payload={"synthetic": True}
    )
    duplicate = store.apply_synthetic_effect(
        "m2", ocs_id="SOFIA", instance_id="i-s", epoch=sofia["epoch"],
        authority_ref="auth:s", idempotency_key="effect-1", payload={"synthetic": True}
    )
    assert first_effect.mutation_count == 1
    assert duplicate.mutation_count == 0
    assert duplicate.duplicate_reconciled is True
    assert store.effect_count("m2") == 1
    engine.dispose()

    restarted_engine = create_engine(f"sqlite+pysqlite:///{db}")
    restarted = Trial2PersistentStore(restarted_engine)
    snapshot = restarted.recover_snapshot("m2", authority_validator=valid_authority)

    assert snapshot.current_primary_actor == "SOFIA"
    assert snapshot.current_instance == "i-s"
    assert snapshot.current_gate == "TRIAL_2"
    assert snapshot.current_handoff_ref == handoff
    assert snapshot.last_valid_checkpoint.startswith("checkpoint:")
    assert snapshot.authority_ref == "auth:s"
    assert snapshot.fencing_epoch == sofia["epoch"]
    assert snapshot.autonomous_step_counter == 1
    assert snapshot.autonomous_handoff_counter == 1
    assert restarted.effect_count("m2") == 1
    assert restarted.observability_count("m2") >= 7


def test_no_checkpoint_for_required_recovery_holds(tmp_path: Path) -> None:
    db = tmp_path / "hold.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{db}")
    store = Trial2PersistentStore(engine)
    store.create_schema()
    store.create_mission(
        "m3", canonical_state_ref="canon", current_gate="TRIAL_2", autonomy_budget=3
    )
    store.bind(
        "m3", "DÉDALA", "i-d", authority_ref="auth", role="architect", activate_if_empty=True
    )
    try:
        store.recover_snapshot("m3", authority_validator=valid_authority)
        raise AssertionError("expected HOLD")
    except Trial2Hold as exc:
        assert str(exc) == "no_checkpoint_for_required_recovery"


def test_cross_ocs_state_write_is_zero(tmp_path: Path) -> None:
    db = tmp_path / "ns.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{db}")
    store = Trial2PersistentStore(engine)
    store.create_schema()
    store.create_mission(
        "m4", canonical_state_ref="canon", current_gate="TRIAL_2", autonomy_budget=3
    )
    binding = store.bind(
        "m4", "DÉDALA", "i-d", authority_ref="auth", role="architect", activate_if_empty=True
    )
    mutation_count = store.write_state(
        "m4", ocs_id="DÉDALA", instance_id="i-d", epoch=binding["epoch"],
        namespace_key="trial2:m4:SOFIA:state:x", value={"bad": 1}
    )
    assert mutation_count == 0
