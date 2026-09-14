from pathlib import Path

from app.materialization.material_plane import (
    DurableEffectStore,
    EffectState,
    FilesystemMaterialProvider,
    MaterialExecutionRequest,
    MaterialPlane,
    Outcome,
)


def _req() -> MaterialExecutionRequest:
    return MaterialExecutionRequest(
        mission_id="M-CRASH",
        logical_operation_id="op-crash",
        effect_id="eff-crash",
        program_id="REIS-OS-AUTONOMOUS-MATERIALIZATION-CLOSURE-001",
        actor="SOFIA",
        bound_object="object://crash",
        expected_object_version="v0",
        capability="fixture_write",
        authorized_intent_hash="crash",
        payload="crash-payload",
        authority_ref="authority://dev",
    )


def test_f001_executing_empty_receipt_absent_file_is_unknown(tmp_path: Path) -> None:
    store = DurableEffectStore(tmp_path / "effects.db")
    store.put(
        effect_id="eff-crash",
        logical_operation_id="op-crash",
        generation=1,
        state=EffectState.EXECUTING.value,
        payload="crash-payload",
        artifact="",
        content_hash="",
        receipt="{}",
        request_identity=_req().identity_digest(),
        expected_version="v0",
        pre_effect_version="v0",
    )
    result = MaterialPlane(
        store=store, provider=FilesystemMaterialProvider(tmp_path / "fx")
    ).execute(_req())
    assert result.outcome is Outcome.EXECUTION_UNKNOWN
    assert result.outcome is not Outcome.SUCCEEDED
    assert result.material is False


def test_f002_orphan_file_is_rediscovered_and_tested(tmp_path: Path) -> None:
    fx = tmp_path / "fx"
    fx.mkdir()
    path = fx / "object_crash.txt"
    path.write_text("crash-payload", encoding="utf-8")
    store = DurableEffectStore(tmp_path / "effects.db")
    store.put(
        effect_id="eff-crash",
        logical_operation_id="op-crash",
        generation=1,
        state=EffectState.EXECUTING.value,
        payload="crash-payload",
        artifact="",
        content_hash="",
        receipt="{}",
        request_identity=_req().identity_digest(),
        expected_version="v0",
        pre_effect_version="v0",
    )
    result = MaterialPlane(
        store=store, provider=FilesystemMaterialProvider(fx)
    ).execute(_req())
    assert result.outcome is Outcome.SUCCEEDED
    assert result.state is EffectState.EVIDENCE_READY
    assert result.replayed is True
    assert result.material is True
    assert path.read_text(encoding="utf-8") == "crash-payload"
    assert result.test_execution_ref
