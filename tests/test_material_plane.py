from pathlib import Path

from app.materialization.material_plane import (
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
    assert result.promoted is False
    assert result.readback is not None
    assert result.readback.reconciliation is Reconciliation.MATCH
    assert Path(result.material_artifact_ref).read_text(encoding="utf-8") == "R$ 25,90"
    assert result.test_execution_ref.startswith("proc:0:")


def test_t04_failing_test_is_not_pass(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(), fail_tests=True)
    assert result.outcome is Outcome.FAILED
    assert result.failure == "tests_failed"


def test_t05_provider_unavailable(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(), provider_available=False)
    assert result.state is EffectState.HOLD
    assert result.failure == "provider_unavailable"


def test_t06_timeout_before_effect_stays_unknown(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(), pretick_timeout=True)
    assert result.outcome is Outcome.EXECUTION_UNKNOWN
    assert result.outcome is not Outcome.SUCCEEDED


def test_t07_t08_timeout_after_effect_then_reconcile(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    unknown = plane.execute(_req(), post_effect_unknown=True)
    assert unknown.outcome is Outcome.EXECUTION_UNKNOWN
    reconciled = plane.reconcile(_req())
    assert reconciled.outcome is Outcome.SUCCEEDED
    assert reconciled.readback is not None
    assert reconciled.readback.reconciliation is Reconciliation.MATCH


def test_t09_replay_same_effect_id_does_not_rewrite(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    first = plane.execute(_req())
    Path(first.material_artifact_ref).write_text("tamper", encoding="utf-8")
    second = plane.execute(_req())
    assert second.replayed is True
    assert Path(first.material_artifact_ref).read_text(encoding="utf-8") == "tamper"


def test_t10_restart_preserves_replay_identity(tmp_path: Path) -> None:
    plane = _plane(tmp_path)
    plane.execute(_req())
    restarted = plane.restart()
    again = restarted.execute(_req())
    assert again.replayed is True


def test_t11_stale_generation_denied(tmp_path: Path) -> None:
    result = _plane(tmp_path, generation=2).execute(_req(generation=1))
    assert result.failure == "stale_generation"


def test_t12_authority_denial(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(actor="UNKNOWN"))
    assert result.state is EffectState.DENIED


def test_t16_provider_cannot_expand_authority(tmp_path: Path) -> None:
    result = _plane(tmp_path).execute(_req(capability="FOUNDER_PROMOTION"))
    assert result.failure == "authority_expansion_denied"
    assert result.promoted is False
