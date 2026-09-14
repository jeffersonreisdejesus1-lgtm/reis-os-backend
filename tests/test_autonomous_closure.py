import sqlite3
from pathlib import Path

from app.materialization.coi import CognitiveOperationalIntegration, CoiDisposition
from app.materialization.factory import FactoryPhase, SoftwareFactory
from app.materialization.recursive_engine import RecursiveEngine


def test_factory_logical_path_is_not_material() -> None:
    receipt = SoftwareFactory().run(actor="SOFIA", mission_id="M1", spec="ledger formatBrl")
    assert receipt.phase == FactoryPhase.QUALIFY_HANDOFF
    assert receipt.material is False
    assert receipt.promoted is False
    assert receipt.qualifies_for_handoff is False
    assert receipt.logical_candidate is True
    assert receipt.evidence[0].passed is False
    assert receipt.evidence[0].readback.startswith("candidate://")


def test_factory_material_path_writes_and_tests(tmp_path: Path) -> None:
    receipt = SoftwareFactory().run(
        actor="SOFIA", mission_id="M-MAT-F", spec="hello-factory", workdir=tmp_path,
        bound_object="object://factory-bound",
    )
    assert receipt.material is True
    assert receipt.promoted is False
    assert receipt.qualifies_for_handoff is True
    assert receipt.bound_object == "object://factory-bound"
    assert Path(receipt.artifact_ref).name == "object_factory-bound.txt"
    assert Path(receipt.artifact_ref).read_text(encoding="utf-8") == "hello-factory"


def test_factory_unavailable_actor_does_not_pass() -> None:
    receipt = SoftwareFactory().run(actor="UNKNOWN", mission_id="M1", spec="x", workdir=Path("/tmp"))
    assert receipt.phase == FactoryPhase.FAILED
    assert receipt.material is False


def test_recursive_sqlite_survives_new_engine(tmp_path: Path) -> None:
    db = tmp_path / "rec.db"
    first = RecursiveEngine(max_depth=3, store_path=db).run(
        actor="SOFIA", mission_id="R1", initial_state="s", goal="s|nudge:1"
    )
    second = RecursiveEngine(max_depth=3, store_path=db).run(
        actor="SOFIA", mission_id="R1", initial_state="s", goal="s|nudge:1"
    )
    assert first.replayed is False
    assert first.authority_gained is False
    assert second.replayed is True
    assert second.termination_reason == "replay_blocked"


def test_recursive_running_after_crash_is_not_completed_replay(tmp_path: Path) -> None:
    db = tmp_path / "rec.db"
    RecursiveEngine(max_depth=3, store_path=db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO recursive_runs(replay_key, status) VALUES (?,?)",
            ("R-CRASH:s:goal", "RUNNING"),
        )
    recovered = RecursiveEngine(max_depth=3, store_path=db).run(
        actor="SOFIA", mission_id="R-CRASH", initial_state="s", goal="goal"
    )
    assert recovered.replayed is False
    assert recovered.failure == "run_interrupted"
    assert recovered.authority_gained is False


def test_coi_material_workdir_sets_material_true(tmp_path: Path) -> None:
    receipt = CognitiveOperationalIntegration().realize(
        actor="SOFIA",
        identity="ocs://sofia",
        intent="hello-coi",
        mission_id="M-COI-MAT",
        bound_object="object://coi",
        workdir=tmp_path,
    )
    assert receipt.disposition == CoiDisposition.CANDIDATE
    assert receipt.promoted is False
    assert receipt.material is True
    assert receipt.failure is None
    artifacts = list((tmp_path / "factory-fx").glob("*.txt"))
    assert artifacts[0].name == "object_coi.txt"
