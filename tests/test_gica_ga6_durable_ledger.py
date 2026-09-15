from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.gica.contracts import (
    AuthorityEvidence,
    GateEvidence,
    GicaGate,
    GicaProgramContract,
    ProgramTransitionError,
    _expected_signature,
    _resolve_institutional_trust,
)
from app.gica.durable_ledger import reset_ledger


def _now() -> datetime:
    return datetime.now(UTC)


def _auth(program: str, operation: str, version: str, now: datetime):
    root = _resolve_institutional_trust()
    if root.authority_key is None:
        pytest.skip("GICA HMAC keys not provisioned")
    unsigned = AuthorityEvidence(
        program,
        operation,
        version,
        "NOESIS-AUTHORITY",
        "SYNESIS-VERIFIER",
        now,
        now + timedelta(hours=1),
        "GICA-AUTHORITY-v1",
        "prov",
        "",
    )
    return unsigned.__class__(
        **{
            **unsigned.__dict__,
            "signature": _expected_signature(unsigned, root.authority_key),
        }
    )


def _gate(program: str, gate: GicaGate, version: str, now: datetime):
    root = _resolve_institutional_trust()
    if root.gate_evidence_key is None:
        pytest.skip("GICA HMAC keys not provisioned")
    unsigned = GateEvidence(
        program,
        gate,
        version,
        f"{gate.name}-CRITERIA-v1",
        ("line-1",),
        "SYNESIS-EVIDENCE",
        "SYNESIS",
        "SYNESIS-VERIFIER",
        now,
        now + timedelta(hours=1),
        "GICA-AUTHORITY-v1",
        "prov",
        True,
        "",
    )
    return unsigned.__class__(
        **{
            **unsigned.__dict__,
            "signature": _expected_signature(unsigned, root.gate_evidence_key),
        }
    )


def test_t03_same_process_replay_returns_successor(tmp_path: Path) -> None:
    reset_ledger(tmp_path / "gica.sqlite")
    now = _now()
    program = "P-GA6-T03"
    version = "v1"
    start = GicaProgramContract(program, GicaGate.GA0, version)
    first = start.transition_to(
        GicaGate.GA1,
        authority=_auth(program, "transition:GA0->GA1", version, now),
        gate_evidence=_gate(program, GicaGate.GA0, version, now),
        now=now,
        operation_id="op-same",
        expected_version=version,
    )
    second = start.transition_to(
        GicaGate.GA1,
        authority=_auth(program, "transition:GA0->GA1", version, now),
        gate_evidence=_gate(program, GicaGate.GA0, version, now),
        now=now,
        operation_id="op-same",
        expected_version=version,
    )
    assert first.gate is GicaGate.GA1
    assert second.gate is GicaGate.GA1
    assert first.committed_generation == second.committed_generation == 1


def test_t02_competing_operation_denied(tmp_path: Path) -> None:
    reset_ledger(tmp_path / "gica.sqlite")
    now = _now()
    program = "P-GA6-T02"
    version = "v1"
    start = GicaProgramContract(program, GicaGate.GA0, version)
    start.transition_to(
        GicaGate.GA1,
        authority=_auth(program, "transition:GA0->GA1", version, now),
        gate_evidence=_gate(program, GicaGate.GA0, version, now),
        now=now,
        operation_id="op-a",
    )
    with pytest.raises(
        ProgramTransitionError, match="canonical_predecessor_already_committed"
    ):
        start.transition_to(
            GicaGate.GA1,
            authority=_auth(program, "transition:GA0->GA1", version, now),
            gate_evidence=_gate(program, GicaGate.GA0, version, now),
            now=now,
            operation_id="op-b",
        )


def test_t08_stale_expected_version_denied(tmp_path: Path) -> None:
    reset_ledger(tmp_path / "gica.sqlite")
    now = _now()
    start = GicaProgramContract("P-STALE", GicaGate.GA0, "v1")
    with pytest.raises(ProgramTransitionError, match="stale_expected_version_denied"):
        start.transition_to(
            GicaGate.GA1,
            authority=_auth("P-STALE", "transition:GA0->GA1", "v1", now),
            gate_evidence=_gate("P-STALE", GicaGate.GA0, "v1", now),
            now=now,
            expected_version="v0",
        )


def test_t14_skip_gate_denied(tmp_path: Path) -> None:
    reset_ledger(tmp_path / "gica.sqlite")
    now = _now()
    start = GicaProgramContract("P-SKIP", GicaGate.GA0, "v1")
    with pytest.raises(
        ProgramTransitionError, match="non_sequential_gate_transition_denied"
    ):
        start.transition_to(
            GicaGate.GA2,
            authority=_auth("P-SKIP", "transition:GA0->GA2", "v1", now),
            gate_evidence=_gate("P-SKIP", GicaGate.GA0, "v1", now),
            now=now,
        )


PROBE = r"""
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.gica.durable_ledger import reset_ledger
from app.gica.contracts import (
    AuthorityEvidence, GateEvidence, GicaGate, GicaProgramContract,
    _expected_signature, _resolve_institutional_trust,
)
reset_ledger(Path(sys.argv[2]))
now = datetime.now(timezone.utc)
root = _resolve_institutional_trust()
program, version = "P-RESTART", "v1"
def auth():
    u = AuthorityEvidence(
        program, "transition:GA0->GA1", version, "NOESIS-AUTHORITY",
        "SYNESIS-VERIFIER", now, now + timedelta(hours=1),
        "GICA-AUTHORITY-v1", "prov", "",
    )
    return u.__class__(
        **{**u.__dict__, "signature": _expected_signature(u, root.authority_key)}
    )
def gate():
    u = GateEvidence(
        program, GicaGate.GA0, version, "GA0-CRITERIA-v1", ("line-1",),
        "SYNESIS-EVIDENCE", "SYNESIS", "SYNESIS-VERIFIER", now,
        now + timedelta(hours=1), "GICA-AUTHORITY-v1", "prov", True, "",
    )
    return u.__class__(
        **{**u.__dict__, "signature": _expected_signature(u, root.gate_evidence_key)}
    )
start = GicaProgramContract(program, GicaGate.GA0, version)
result = start.transition_to(
    GicaGate.GA1, authority=auth(), gate_evidence=gate(), now=now,
    operation_id="op-restart",
)
print(json.dumps({
    "pid": os.getpid(), "gate": result.gate.value,
    "generation": result.committed_generation,
}))
"""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "app" / "gica" / "contracts.py").exists():
            return parent
    return Path.cwd()


def test_t04_t06_t07_new_process_replay_no_new_effect(tmp_path: Path) -> None:
    if not os.environ.get("GICA_AUTHORITY_HMAC_KEY"):
        pytest.skip("GICA HMAC keys not provisioned")
    repo = _repo_root()
    db = tmp_path / "gica.sqlite"
    env = os.environ.copy()
    p1 = subprocess.run(
        [sys.executable, "-c", PROBE, str(repo), str(db)],
        capture_output=True,
        text=True,
        cwd=str(repo),
        env=env,
    )
    p2 = subprocess.run(
        [sys.executable, "-c", PROBE, str(repo), str(db)],
        capture_output=True,
        text=True,
        cwd=str(repo),
        env=env,
    )
    assert p1.returncode == 0, p1.stderr
    assert p2.returncode == 0, p2.stderr
    a = json.loads(p1.stdout.strip().splitlines()[-1])
    b = json.loads(p2.stdout.strip().splitlines()[-1])
    assert a["pid"] != b["pid"]
    assert a["gate"] == b["gate"] == "GA1_SPECIFICATION_CONSISTENCY"
    assert a["generation"] == b["generation"] == 1


def test_t02_real_process_concurrency_single_successor(tmp_path: Path) -> None:
    if not os.environ.get("GICA_AUTHORITY_HMAC_KEY"):
        pytest.skip("GICA HMAC keys not provisioned")
    repo = _repo_root()
    db = tmp_path / "gica-concurrent.sqlite"
    env = os.environ.copy()
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", PROBE, str(repo), str(db)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(repo),
            env=env,
        )
        for _ in range(2)
    ]
    results = [process.communicate(timeout=30) for process in processes]
    assert all(process.returncode == 0 for process in processes), results
    payloads = [
        json.loads(stdout.strip().splitlines()[-1]) for stdout, _stderr in results
    ]
    assert {item["gate"] for item in payloads} == {"GA1_SPECIFICATION_CONSISTENCY"}
    assert {item["generation"] for item in payloads} == {1}
    assert payloads[0]["pid"] != payloads[1]["pid"]


def test_t07_ledger_reconstructs_single_canonical_successor(tmp_path: Path) -> None:
    path = tmp_path / "gica-reconstruct.sqlite"
    durable = reset_ledger(path)
    predecessor = ("P-RECONSTRUCT", "v1", "GA0_BOOTSTRAP", "ACTIVE", (), 0)
    first = durable.commit_transition(predecessor, "op-canonical", '{"gate":"GA1"}')
    reopened = type(durable)(path)
    second = reopened.commit_transition(predecessor, "op-other", '{"gate":"GA1-other"}')
    assert first == second
    assert reopened.get_transition(predecessor) == first
