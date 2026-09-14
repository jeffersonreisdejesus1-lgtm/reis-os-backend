from pathlib import Path

from app.materialization.coi import CognitiveOperationalIntegration, CoiDisposition
from app.materialization.factory import FactoryPhase, SoftwareFactory
from app.materialization.recursive_engine import RecursiveEngine


def test_factory_logical_path_is_not_material() -> None:
    receipt = SoftwareFactory().run(actor="SOFIA", mission_id="M1", spec="ledger formatBrl")
    assert receipt.phase == FactoryPhase.QUALIFY_HANDOFF
    assert receipt.material is False
    assert receipt.promoted is False
    assert receipt.evidence[0].passed is False
    assert receipt.evidence[0].readback.startswith("candidate://")


def test_factory_material_path_writes_and_tests(tmp_path: Path) -> None:
    receipt = SoftwareFactory().run(
        actor="SOFIA", mission_id="M-MAT-F", spec="hello-factory", workdir=tmp_path
    )
    assert receipt.material is True
    assert receipt.promoted is False
    assert receipt.phase == FactoryPhase.QUALIFY_HANDOFF
    assert Path(receipt.artifact_ref).read_text(encoding="utf-8") == "hello-factory"
    assert receipt.evidence[1].passed is True
    assert "tests_executed" not in receipt.evidence[1].readback


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
