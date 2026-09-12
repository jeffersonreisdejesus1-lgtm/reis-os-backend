from types import SimpleNamespace

import pytest

from app.cognitive_validation.operational_learning_loop import ClosedOperationalLearningLoop
from app.cognitive_validation.persistent_learning_runtime import (
    PersistentClosedOperationalLearningRuntime,
    PersistentOperationalLearningError,
    PersistentOperationalLearningStore,
)


def _coi11_result(*, mission_id="mission-1", state_hash="state-2", state_version=2):
    evidence = SimpleNamespace(
        mission_id=mission_id,
        evidence_receipt="evidence-2",
    )
    state_snapshot = SimpleNamespace(
        mission_id=mission_id,
        evidence_receipt="evidence-2",
        state_hash=state_hash,
        state_version=state_version,
    )
    return SimpleNamespace(evidence=evidence, state_snapshot=state_snapshot)


def test_failure_learning_persists_and_is_consumed_after_runtime_restart(tmp_path):
    db = tmp_path / "learning.sqlite3"
    previous = ClosedOperationalLearningLoop.initial_plan(
        mission_id="mission-1", capability_id="github", state_hash="state-1"
    )

    store_n = PersistentOperationalLearningStore(db)
    runtime_n = PersistentClosedOperationalLearningRuntime(store=store_n)
    learned = runtime_n.close_loop_and_commit(
        previous_plan=previous,
        coi11_result=_coi11_result(),
        candidate_capabilities=("github", "software_factory"),
        outcome="FAILURE",
    )
    assert learned.route_changed is True
    assert learned.next_plan.selected_capability_id == "software_factory"
    store_n.close()

    # New store/runtime instance proves the learned decision crossed a process boundary.
    store_n1 = PersistentOperationalLearningStore(db)
    runtime_n1 = PersistentClosedOperationalLearningRuntime(store=store_n1)
    resumed = runtime_n1.resume_for_next_mission(
        mission_id="mission-1",
        expected_learning_receipt=learned.learning_receipt,
    )
    assert resumed.plan_revision == 2
    assert resumed.prior_plan_receipt == previous.plan_receipt
    assert resumed.state_hash == "state-2"
    assert resumed.selected_capability_id == "software_factory"
    assert resumed.selected_capability_id != previous.selected_capability_id
    store_n1.close()


def test_restart_fails_closed_on_wrong_learning_receipt(tmp_path):
    db = tmp_path / "learning.sqlite3"
    previous = ClosedOperationalLearningLoop.initial_plan(
        mission_id="mission-1", capability_id="github", state_hash="state-1"
    )
    store = PersistentOperationalLearningStore(db)
    runtime = PersistentClosedOperationalLearningRuntime(store=store)
    runtime.close_loop_and_commit(
        previous_plan=previous,
        coi11_result=_coi11_result(),
        candidate_capabilities=("github", "software_factory"),
        outcome="PARTIAL",
    )
    store.close()

    reopened = PersistentOperationalLearningStore(db)
    restarted = PersistentClosedOperationalLearningRuntime(store=reopened)
    with pytest.raises(PersistentOperationalLearningError, match="receipt_mismatch"):
        restarted.resume_for_next_mission(
            mission_id="mission-1", expected_learning_receipt="forged-learning-receipt"
        )
    reopened.close()


def test_persistent_learning_rejects_non_monotonic_or_broken_lineage(tmp_path):
    db = tmp_path / "learning.sqlite3"
    previous = ClosedOperationalLearningLoop.initial_plan(
        mission_id="mission-1", capability_id="github", state_hash="state-1"
    )
    store = PersistentOperationalLearningStore(db)
    runtime = PersistentClosedOperationalLearningRuntime(store=store)
    first = runtime.close_loop_and_commit(
        previous_plan=previous,
        coi11_result=_coi11_result(),
        candidate_capabilities=("github", "software_factory"),
        outcome="FAILURE",
    )

    # Recommitting the same qualified result must not overwrite durable state.
    with pytest.raises(PersistentOperationalLearningError, match="revision_not_monotonic"):
        store.commit(first)
    store.close()


def test_missing_persistent_state_does_not_fallback_to_in_memory_plan(tmp_path):
    store = PersistentOperationalLearningStore(tmp_path / "empty.sqlite3")
    runtime = PersistentClosedOperationalLearningRuntime(store=store)
    with pytest.raises(PersistentOperationalLearningError, match="state_not_found"):
        runtime.resume_for_next_mission(
            mission_id="mission-1", expected_learning_receipt="expected"
        )
    store.close()
