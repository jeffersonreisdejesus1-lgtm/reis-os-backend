from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.gica.ga7_authority import Ga7AuthorityToken
from app.gica.ga7_controls import SHARED_BUDGET_KEY, Ga7BudgetEnvelope
from app.gica.ga7_corpus import Ga7Baseline, Ga7Corpus
from app.gica.ga7_ledger import Ga7Ledger, Ga7LedgerError
from app.gica.ga7_runtime import Ga7HostBinding, Ga7Runtime, Ga7RuntimeManifest
from app.gica.ga7_types import (
    BOUND_HEAD,
    CONTRACT_ID,
    Ga7CaseState,
    Ga7DiscoveryCaseInput,
    Ga7Disposition,
)

NOW = datetime(2026, 9, 14, 4, 0, tzinfo=timezone.utc)


def _case(**overrides) -> Ga7DiscoveryCaseInput:
    base = dict(
        program_id="GICA",
        gate_id="GA7",
        contract_id=CONTRACT_ID,
        mission_id="M-GA7",
        saga_id="S1",
        logical_operation_id="op-1",
        discovery_case_id="C1",
        case_version="v1",
        bound_head=BOUND_HEAD,
        object_version="obj-1",
        policy_version="GICA-AUTHORITY-v1",
        discovery_corpus_ref="corpus://open",
        discovery_corpus_version="1",
        task_class="discovery",
        mission_class="pilot",
        risk_class="low",
        effect_class="NONMATERIAL",
        input_artifact_refs=("a://1",),
        expected_outcome_schema="observed",
        participating_specialties=("SOFIA",),
        authority_ref="authority://dev",
        authority_scope="DISCOVERY_CASE_NONMATERIAL",
        capability_bindings=("observe",),
        runtime_refs=("host://test",),
        budget_ref="budget://1",
        stop_rules_ref="stop://1",
        evidence_ledger_ref="ledger://ga7",
        trace_id="t1",
        correlation_id="c1",
        generation=1,
        fencing_epoch=1,
        attempt_id="att-1",
        replay_of="",
        recovery_scenario="",
        baseline_required=True,
        baseline_ref="base://1",
        baseline_version="1",
        material_effect_allowed=False,
        max_parallelism=1,
        max_recursion_depth=0,
    )
    base.update(overrides)
    return Ga7DiscoveryCaseInput(**base)


def _token(**overrides) -> Ga7AuthorityToken:
    base = dict(
        program_id="GICA",
        gate_id="GA7",
        bound_head=BOUND_HEAD,
        object_version="obj-1",
        policy_version="GICA-AUTHORITY-v1",
        operation="DISCOVERY_CASE_NONMATERIAL",
        issuer="NOESIS-AUTHORITY",
        verifier="SYNESIS-VERIFIER",
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        scope="DISCOVERY_CASE_NONMATERIAL",
    )
    base.update(overrides)
    return Ga7AuthorityToken(**base)


def _envelope(**overrides) -> Ga7BudgetEnvelope:
    base = dict(
        MAX_DISCOVERY_CASES=2,
        MAX_OCS_CALLS=10,
        MAX_AGENT_RUNS=10,
        MAX_MODEL_CALLS=10,
        MAX_TOOL_CALLS=10,
        MAX_RETRIES=1,
        MAX_REPAIR_EPOCHS=1,
        MAX_PARALLELISM=1,
        MAX_RECURSION_DEPTH=0,
        MAX_COST=1.0,
        MAX_ELAPSED_TIME=60.0,
        MAX_PIVOTS=1,
    )
    base.update(overrides)
    return Ga7BudgetEnvelope(**base)


def _corpus() -> Ga7Corpus:
    return Ga7Corpus(
        ref="corpus://open",
        version="1",
        content_hash="abc",
        case_ids=frozenset({"C1"}),
        holdout_classification="OPEN",
        policy_version="GICA-AUTHORITY-v1",
        bound_head=BOUND_HEAD,
    )


def _baseline() -> Ga7Baseline:
    return Ga7Baseline("base://1", "1", "hash", "HISTORICAL", True)


def _runtime(tmp_path: Path) -> Ga7Runtime:
    ledger = Ga7Ledger(tmp_path / "ga7.sqlite")
    manifest = Ga7RuntimeManifest(
        runtime_id="test", runtime_version="1", exact_head=BOUND_HEAD,
        specialties=frozenset({"SOFIA"}), capabilities=frozenset({"observe"}),
    )
    return Ga7Runtime(ledger, manifest)


def _run(tmp_path, case=None, token=None, envelope=None, **kwargs):
    return _runtime(tmp_path).execute(
        case or _case(), token if token is not None else _token(), envelope or _envelope(),
        _corpus(), _baseline(), **kwargs,
    )


def test_t01_valid_case(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.disposition is Ga7Disposition.OBSERVED
    assert result.promoted is False
    assert result.ga7_entered is False


def test_t02_invalid_schema() -> None:
    ok, reason = _case(program_id="").validate()
    assert ok is False
    assert reason == "missing_program_id"


def test_t03_absent_authority(tmp_path: Path) -> None:
    result = _run(tmp_path, token=None)
    assert result.disposition is Ga7Disposition.DENIED
    assert result.failure == "absent_authority"


def test_t04_forged_or_stale_authority(tmp_path: Path) -> None:
    stale = _token(expires_at=NOW - timedelta(seconds=1))
    result = _run(tmp_path, token=stale)
    assert result.failure == "stale_authority"
    forged = _token(issuer="SOFIA")
    assert _run(tmp_path, case=_case(discovery_case_id="C1", case_version="v-forged"), token=forged).failure == "untrusted_issuer_or_verifier"


def test_t05_wrong_bound_head() -> None:
    ok, reason = _case(bound_head="deadbeef").validate()
    assert reason == "wrong_bound_head"


def test_t06_invalid_policy() -> None:
    ok, reason = _case(policy_version="OTHER").validate()
    assert reason == "wrong_policy"


def test_t07_t08_same_process_replay_idempotent(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    first = runtime.execute(_case(), _token(), _envelope(), _corpus(), _baseline())
    second = runtime.replay(_case())
    assert first.identity_hash == second.identity_hash
    assert len(runtime.ledger.receipts(_case().case_key())) >= 1


def test_t09_t28_t30_restart_readback(tmp_path: Path) -> None:
    db = tmp_path / "ga7.sqlite"
    first = Ga7Runtime(Ga7Ledger(db), Ga7RuntimeManifest("t", "1", BOUND_HEAD, frozenset({"SOFIA"}), frozenset({"observe"})))
    produced = first.execute(_case(), _token(), _envelope(), _corpus(), _baseline())
    second = Ga7Runtime(Ga7Ledger(db), Ga7RuntimeManifest("t", "1", BOUND_HEAD, frozenset({"SOFIA"}), frozenset({"observe"})))
    loaded = second.replay(_case())
    assert loaded.identity_hash == produced.identity_hash
    assert second.ledger.get_budget(SHARED_BUDGET_KEY)["case"] == 1


def test_t10_duplicate_receipt_idempotent(tmp_path: Path) -> None:
    ledger = Ga7Ledger(tmp_path / "ga7.sqlite")
    case = _case()
    ledger.bind_case(case)
    from app.gica.ga7_types import Ga7EpistemicClass, Ga7ReceiptType
    h1 = ledger.append_receipt(receipt_id="r1", case_key=case.case_key(), receipt_type=Ga7ReceiptType.ACTION, epistemic=Ga7EpistemicClass.OBSERVED, payload={"x": 1})
    h2 = ledger.append_receipt(receipt_id="r1", case_key=case.case_key(), receipt_type=Ga7ReceiptType.ACTION, epistemic=Ga7EpistemicClass.OBSERVED, payload={"x": 1})
    assert h1 == h2
    assert len(ledger.receipts(case.case_key())) == 1


def test_t11_conflicting_receipt_hold(tmp_path: Path) -> None:
    ledger = Ga7Ledger(tmp_path / "ga7.sqlite")
    case = _case()
    ledger.bind_case(case)
    from app.gica.ga7_types import Ga7EpistemicClass, Ga7ReceiptType
    ledger.append_receipt(receipt_id="r1", case_key=case.case_key(), receipt_type=Ga7ReceiptType.ACTION, epistemic=Ga7EpistemicClass.OBSERVED, payload={"x": 1})
    with pytest.raises(Ga7LedgerError, match="conflicting_receipt"):
        ledger.append_receipt(receipt_id="r1", case_key=case.case_key(), receipt_type=Ga7ReceiptType.ACTION, epistemic=Ga7EpistemicClass.OBSERVED, payload={"x": 2})


def test_t12_budget_exhaustion(tmp_path: Path) -> None:
    env = _envelope(MAX_DISCOVERY_CASES=1)
    runtime = _runtime(tmp_path)
    runtime.execute(_case(), _token(), env, _corpus(), _baseline())
    second = runtime.execute(_case(case_version="v2"), _token(), env, _corpus(), _baseline())
    assert second.failure == "budget_exhausted"


def test_t13_timeout(tmp_path: Path) -> None:
    assert _run(tmp_path, force_timeout=True).failure == "timeout"


def test_t14_stop_condition(tmp_path: Path) -> None:
    assert _run(tmp_path, envelope=_envelope(MAX_DISCOVERY_CASES=0)).failure == "budget_exhausted"


def test_t15_t16_unknown_and_reconcile(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    unknown = runtime.execute(_case(), _token(), _envelope(), _corpus(), _baseline(), force_unknown=True)
    assert unknown.state is Ga7CaseState.UNKNOWN
    recon = runtime.reconcile_unknown(_case())
    assert recon.state is Ga7CaseState.STILL_UNKNOWN


def test_t17_evidence_readback_failure(tmp_path: Path) -> None:
    assert _run(tmp_path, force_readback_failure=True).failure == "evidence_readback_failure"


def test_t18_missing_baseline(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    result = runtime.execute(_case(), _token(), _envelope(), _corpus(), None)
    assert result.failure == "missing_baseline"


def test_t19_corrupt_ledger(tmp_path: Path) -> None:
    ledger = Ga7Ledger(tmp_path / "ga7.sqlite")
    case = _case()
    ledger.bind_case(case)
    import sqlite3
    with sqlite3.connect(ledger.path) as conn:
        conn.execute("UPDATE ga7_cases SET result_json=? WHERE case_key=?", ("{", case.case_key()))
    with pytest.raises(Ga7LedgerError, match="corrupt_ledger_record"):
        ledger.load_result(case.case_key())


def test_t20_self_promotion_denied(tmp_path: Path) -> None:
    assert _run(tmp_path, request_self_promote=True).failure == "self_promotion_denied"


def test_t21_ga7_entry_denied(tmp_path: Path) -> None:
    assert _run(tmp_path, request_ga7_entry=True).failure == "ga7_entry_denied"


def test_t22_material_effect_denied(tmp_path: Path) -> None:
    assert _run(tmp_path, request_material=True).failure == "material_effect_denied"


def test_t23_parallelism_denied(tmp_path: Path) -> None:
    assert _run(tmp_path, request_parallel=True).failure == "parallelism_denied"


def test_t24_recursion_denied(tmp_path: Path) -> None:
    assert _run(tmp_path, request_recursion=True).failure == "recursion_denied"


def test_t25_unavailable_specialty(tmp_path: Path) -> None:
    result = _run(tmp_path, case=_case(participating_specialties=("LYRA",)))
    assert result.failure == "unavailable_specialty_or_capability"


def test_t26_corpus_membership_failure(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    result = runtime.execute(_case(discovery_case_id="CX"), _token(), _envelope(), _corpus(), _baseline())
    assert result.failure == "corpus_membership_failure"


def test_t27_sealed_holdout(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    sealed = Ga7Corpus("corpus://open", "1", "abc", frozenset({"C1"}), "GA9_SEALED", "GICA-AUTHORITY-v1", BOUND_HEAD, True)
    result = runtime.execute(_case(), _token(), _envelope(), sealed, _baseline())
    assert result.failure == "sealed_holdout_contamination"


def test_t29_replay_no_new_evidence_credit(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.execute(_case(), _token(), _envelope(), _corpus(), _baseline())
    before = len(runtime.ledger.receipts(_case().case_key()))
    runtime.replay(_case())
    after = len(runtime.ledger.receipts(_case().case_key()))
    assert after == before


def test_host_preflight_negative(tmp_path: Path) -> None:
    ledger = Ga7Ledger(tmp_path / "ga7.sqlite")
    bad = Ga7RuntimeManifest("x", "1", "wrong", frozenset(), frozenset(), material_effect_capable=True, max_parallelism=2)
    result = Ga7HostBinding(bad, ledger, False).preflight()
    assert result.status == "HOLD"
    assert "wrong_head" in result.reasons
