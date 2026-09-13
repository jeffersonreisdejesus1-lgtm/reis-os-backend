import json
from pathlib import Path

from app.materialization.material_plane import (
    AUTHORITY_REF_VALIDATED,
    DurableEffectStore,
    EffectState,
    FilesystemMaterialProvider,
    MaterialExecutionRequest,
    MaterialPlane,
    Outcome,
    Reconciliation,
)


def _plane(tmp_path: Path, generation: int = 1) -> MaterialPlane:
    return MaterialPlane(
        store=DurableEffectStore(tmp_path / "effects.db"),
        provider=FilesystemMaterialProvider(tmp_path / "fx"),
        live_generation=generation,
    )


def _req(**overrides) -> MaterialExecutionRequest:
    base = dict(
        mission_id="M-MAT",
        logical_operation_id="op-1",
        effect_id="eff-1",
        program_id="REIS-OS-MATERIAL-CLOSURE-SLICE-001",
        actor="SOFIA",
        bound_object="object://fixture-ledger",
        expected_object_version="v0",
        capability="fixture_write",
        authorized_intent_hash="intent-1",
        payload="R$ 25,90",
        authority_ref="authority://dev",
        generation=1,
    )
    base.update(overrides)
    return MaterialExecutionRequest(**base)


def test_t01_t02_t03_real_write_readback_and_tests(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req())
    assert result.outcome is Outcome.SUCCEEDED
    assert result.material is True
    assert result.readback is not None
    assert result.readback.reconciliation is Reconciliation.MATCH
    assert Path(result.material_artifact_ref).read_text(encoding="utf-8") == "R$ 25,90"
    provenance = json.loads(result.test_execution_ref)
    assert provenance["returncode"] == 0
    assert AUTHORITY_REF_VALIDATED is False


def test_t04_failing_test_is_not_pass(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(), fail_tests=True)
    assert result.outcome is Outcome.FAILED
    assert result.material is True


def test_t05_provider_unavailable(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(), provider_available=False)
    assert result.state is EffectState.HOLD
    assert result.material is False


def test_t06_timeout_before_effect_stays_unknown(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(), pretick_timeout=True)
    assert result.outcome is Outcome.EXECUTION_UNKNOWN
    assert result.material is False


def test_t07_t08_timeout_after_effect_then_reconcile(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    unknown = plane.execute(_req(), post_effect_unknown=True)
    assert unknown.outcome is Outcome.EXECUTION_UNKNOWN
    assert unknown.material is True
    reconciled = plane.reconcile(_req())
    assert reconciled.outcome is Outcome.SUCCEEDED
    assert reconciled.material is True


def test_t09_t23_tamper_replay_is_drift_without_rewrite(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    first = plane.execute(_req())
    Path(first.material_artifact_ref).write_text("tamper", encoding="utf-8")
    second = plane.execute(_req())
    assert second.replayed is True
    assert second.state is EffectState.MATERIAL_DRIFT
    assert second.material is True
    assert Path(first.material_artifact_ref).read_text(encoding="utf-8") == "tamper"


def test_t10_restart_new_store_object(tmp_path: Path) -> None:
    _plane(tmp_path).execute(_req())
    again = _plane(tmp_path).execute(_req())
    assert again.replayed is True
    assert again.material is True


def test_t11_stale_generation_denied(tmp_path: Path) -> None:
    result = _plane(tmp_path, generation=2).execute(_req(generation=1))
    assert result.failure == "stale_generation"
    assert result.material is False


def test_t12_authority_denial(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(actor="UNKNOWN"))
    assert result.state is EffectState.DENIED
    assert result.material is False


def test_t16_provider_cannot_expand_authority(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(capability="FOUNDER_PROMOTION"))
    assert result.failure == "authority_expansion_denied"
    assert result.material is False


def test_t17_same_effect_different_payload_conflict(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    plane.execute(_req())
    conflict = plane.execute(_req(payload="other"))
    assert conflict.failure == "effect_identity_conflict"
    assert conflict.material is False
    assert conflict.replayed is False


def test_t18_different_intent_hash_conflict(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    plane.execute(_req())
    assert plane.execute(_req(authorized_intent_hash="other")).material is False


def test_t19_different_object_conflict(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    plane.execute(_req())
    assert plane.execute(_req(bound_object="object://other")).material is False


def test_t20_t21_expected_version_enforced(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    first = plane.execute(_req())
    digest = Path(first.material_artifact_ref)
    content_hash = __import__("hashlib").sha256(digest.read_bytes()).hexdigest()
    stale = plane.execute(_req(effect_id="eff-2", expected_object_version="v0", logical_operation_id="op-2"))
    assert stale.failure == "version_conflict"
    assert stale.material is False
    ok = plane.execute(_req(effect_id="eff-3", logical_operation_id="op-3", expected_object_version=content_hash, payload="next"))
    assert ok.outcome is Outcome.SUCCEEDED
    assert ok.material is True


def test_t22_candidate_namespace_does_not_write(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    result = plane.execute(_req(bound_object="candidate://ledger"))
    assert result.failure == "non_material_object_namespace"
    assert result.material is False
    fx = tmp_path / "fx"
    if fx.exists():
        assert list(fx.glob("*")) == []


def test_t24_new_process_equivalent_new_store_replay(tmp_path: Path) -> None:
    db = tmp_path / "effects.db"
    fx = tmp_path / "fx"
    first = MaterialPlane(store=DurableEffectStore(db), provider=FilesystemMaterialProvider(fx))
    written = first.execute(_req())
    assert written.material is True
    second = MaterialPlane(store=DurableEffectStore(db), provider=FilesystemMaterialProvider(fx))
    replay = second.execute(_req())
    assert replay.replayed is True
    assert replay.material is True


def test_t25_provenance_binds_command_and_digests(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req())
    body = json.loads(result.test_execution_ref)
    assert body["command"][-1].endswith(".probe.py")
    assert result.material is True


def test_t26_exact_intent_replay_includes_readback(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    plane.execute(_req())
    replay = plane.execute(_req())
    assert replay.replayed is True
    assert replay.material is True
    assert replay.readback is not None
    assert replay.readback.reconciliation is Reconciliation.MATCH


def test_t27_same_effect_different_capability_conflict(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    plane.execute(_req())
    conflict = plane.execute(_req(capability="other_write"))
    assert conflict.failure == "effect_identity_conflict"
    assert conflict.material is False


def test_t28_same_effect_different_logical_operation_conflict(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    plane.execute(_req())
    conflict = plane.execute(_req(logical_operation_id="op-other"))
    assert conflict.failure == "effect_identity_conflict"
    assert conflict.material is False
