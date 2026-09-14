from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from app.materialization.authority import AuthorityBoundary, MutationKind

AUTHORITY_REF_VALIDATED = False
INITIAL_OBJECT_VERSION = "v0"
NONTERMINAL_STATES = {
    "EXECUTING",
    "EXECUTION_UNKNOWN",
    "READBACK_PENDING",
    "RECONCILING",
    "UNKNOWN",
}


class Outcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    EXECUTION_UNKNOWN = "EXECUTION_UNKNOWN"


class Reconciliation(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class EffectState(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    DISPATCHING = "DISPATCHING"
    EXECUTING = "EXECUTING"
    EFFECT_REPORTED = "EFFECT_REPORTED"
    FAILED = "FAILED"
    EXECUTION_UNKNOWN = "EXECUTION_UNKNOWN"
    READBACK_PENDING = "READBACK_PENDING"
    RECONCILING = "RECONCILING"
    RECONCILED_SUCCESS = "RECONCILED_SUCCESS"
    RECONCILED_FAILURE = "RECONCILED_FAILURE"
    UNKNOWN = "UNKNOWN"
    TESTING = "TESTING"
    EVIDENCE_READY = "EVIDENCE_READY"
    DENIED = "DENIED"
    HOLD = "HOLD"
    MATERIAL_DRIFT = "MATERIAL_DRIFT"


@dataclass(frozen=True, slots=True)
class MaterialExecutionRequest:
    mission_id: str
    logical_operation_id: str
    effect_id: str
    program_id: str
    actor: str
    bound_object: str
    expected_object_version: str
    capability: str
    authorized_intent_hash: str
    payload: str
    authority_ref: str
    generation: int = 1

    def identity_digest(self) -> str:
        canonical = json.dumps(
            {
                "mission_id": self.mission_id,
                "logical_operation_id": self.logical_operation_id,
                "effect_id": self.effect_id,
                "program_id": self.program_id,
                "actor": self.actor,
                "bound_object": self.bound_object,
                "expected_object_version": self.expected_object_version,
                "capability": self.capability,
                "authorized_intent_hash": self.authorized_intent_hash,
                "authority_ref": self.authority_ref,
                "generation": self.generation,
                "payload_digest": sha256(self.payload.encode()).hexdigest(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class MaterialReadback:
    effect_id: str
    source: str
    observed_object_version: str
    observed_hash: str
    observed_state: str
    timestamp: float
    reconciliation: Reconciliation
    pre_effect_version: str = ""
    expected_version: str = ""


@dataclass(frozen=True, slots=True)
class MaterialExecutionResult:
    operation_id: str
    effect_id: str
    provider_identity: str
    started_at: float
    completed_at: float | None
    unknown_at: float | None
    outcome: Outcome
    state: EffectState
    material_artifact_ref: str
    observed_object_version: str
    execution_hash: str
    test_execution_ref: str
    raw_receipt_ref: str
    readback: MaterialReadback | None
    replayed: bool
    promoted: bool
    failure: str | None
    material: bool
    authority_ref_validated: bool = AUTHORITY_REF_VALIDATED


class DurableEffectStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS effects (
                    effect_id TEXT PRIMARY KEY,
                    logical_operation_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    artifact TEXT,
                    content_hash TEXT,
                    receipt TEXT,
                    request_identity TEXT,
                    expected_version TEXT,
                    pre_effect_version TEXT
                )"""
            )
            cols = {row[1] for row in conn.execute("PRAGMA table_info(effects)")}
            for name in ("request_identity", "expected_version", "pre_effect_version"):
                if name not in cols:
                    conn.execute(f"ALTER TABLE effects ADD COLUMN {name} TEXT")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, effect_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM effects WHERE effect_id=?", (effect_id,)).fetchone()

    def put(self, **fields: object) -> None:
        keys = ",".join(fields)
        marks = ",".join("?" * len(fields))
        with self._conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO effects ({keys}) VALUES ({marks})",
                tuple(fields.values()),
            )


class FilesystemMaterialProvider:
    identity = "filesystem-fixture-provider"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def artifact_path(self, bound_object: str) -> Path:
        safe = bound_object.replace("://", "_").replace("/", "_")
        return self.root / f"{safe}.txt"

    def pre_effect_version(self, bound_object: str) -> tuple[str, bool]:
        path = self.artifact_path(bound_object)
        if not path.exists():
            return INITIAL_OBJECT_VERSION, True
        try:
            digest = sha256(path.read_bytes()).hexdigest()
        except OSError:
            return "UNKNOWN", False
        return digest, True

    def apply(self, request: MaterialExecutionRequest) -> tuple[Path, str]:
        path = self.artifact_path(request.bound_object)
        path.write_text(request.payload, encoding="utf-8")
        return path, sha256(path.read_bytes()).hexdigest()

    def readback(self, request: MaterialExecutionRequest, expected_hash: str) -> MaterialReadback:
        path = self.artifact_path(request.bound_object)
        if not path.exists():
            return MaterialReadback(
                request.effect_id, str(path), "", "", "ABSENT", time.time(), Reconciliation.ABSENT
            )
        observed = path.read_text(encoding="utf-8")
        digest = sha256(observed.encode()).hexdigest()
        match = bool(expected_hash) and digest == expected_hash and observed == request.payload
        return MaterialReadback(
            request.effect_id,
            str(path),
            digest[:12],
            digest,
            observed,
            time.time(),
            Reconciliation.MATCH if match else Reconciliation.MISMATCH,
        )

    def run_tests(self, request: MaterialExecutionRequest, artifact: Path) -> tuple[str, bool]:
        probe = artifact.with_suffix(".probe.py")
        body = (
            "from pathlib import Path\n"
            f"p = Path({str(artifact)!r})\n"
            f"assert p.read_text(encoding='utf-8') == {request.payload!r}\n"
        )
        probe.write_text(body, encoding="utf-8")
        command = [sys.executable, str(probe)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        provenance = {
            "command": command,
            "returncode": completed.returncode,
            "stdout_digest": sha256(completed.stdout.encode()).hexdigest(),
            "stderr_digest": sha256(completed.stderr.encode()).hexdigest(),
            "probe_digest": sha256(body.encode()).hexdigest(),
            "artifact_digest": sha256(artifact.read_bytes()).hexdigest() if artifact.exists() else "",
        }
        return json.dumps(provenance, sort_keys=True, separators=(",", ":")), completed.returncode == 0


class MaterialPlane:
    def __init__(self, *,
                 store: DurableEffectStore,
                 provider: FilesystemMaterialProvider,
                 boundary: AuthorityBoundary | None = None,
                 live_generation: int = 1) -> None:
        self._store = store
        self._provider = provider
        self._boundary = boundary or AuthorityBoundary()
        self._generation = live_generation

    def execute(self, request: MaterialExecutionRequest, *,
                provider_available: bool = True,
                pretick_timeout: bool = False,
                post_effect_unknown: bool = False,
                fail_tests: bool = False) -> MaterialExecutionResult:
        started = time.time()
        if request.bound_object.startswith("candidate://"):
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED,
                                failure="non_material_object_namespace")
        auth = self._boundary.decide(actor=request.actor, kind=MutationKind.EDIT_FILE)
        if not auth.allowed:
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED, failure=auth.reason)
        if request.generation != self._generation:
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED, failure="stale_generation")
        if request.capability in {"GITHUB_MERGE_PR", "FOUNDER_PROMOTION", "GATE_PROMOTION"}:
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED,
                                failure="authority_expansion_denied")
        if not provider_available:
            return self._result(request, started, Outcome.FAILED, EffectState.HOLD,
                                failure="provider_unavailable")

        existing = self._store.get(request.effect_id)
        if existing is not None:
            return self._replay(request, existing, started)

        pre_version, readable = self._provider.pre_effect_version(request.bound_object)
        if not readable:
            return self._result(request, started, Outcome.EXECUTION_UNKNOWN, EffectState.HOLD,
                                failure="pre_effect_version_unknown")
        if request.expected_object_version != pre_version:
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED,
                                failure="version_conflict")

        if pretick_timeout:
            self._record(request, EffectState.EXECUTION_UNKNOWN, "", "",
                         {"outcome": Outcome.EXECUTION_UNKNOWN.value}, pre_version)
            return self._result(request, started, Outcome.EXECUTION_UNKNOWN, EffectState.EXECUTION_UNKNOWN,
                                unknown_at=time.time(), failure="timeout_before_known_effect")

        self._record(request, EffectState.EXECUTING, "", "", {}, pre_version)
        path, digest = self._provider.apply(request)
        if post_effect_unknown:
            self._record(request, EffectState.EXECUTION_UNKNOWN, str(path), digest,
                         {"outcome": Outcome.EXECUTION_UNKNOWN.value}, pre_version)
            return self._result(request, started, Outcome.EXECUTION_UNKNOWN, EffectState.RECONCILING,
                                artifact=str(path), digest=digest, unknown_at=time.time(),
                                failure="timeout_after_potential_effect")

        observed = self._provider.readback(request, digest)
        if observed.reconciliation != Reconciliation.MATCH:
            self._record(request, EffectState.RECONCILED_FAILURE, str(path), digest,
                         {"outcome": Outcome.FAILED.value}, pre_version)
            return self._result(request, started, Outcome.FAILED, EffectState.RECONCILED_FAILURE,
                                artifact=str(path), digest=digest, readback=observed,
                                failure="readback_mismatch")

        test_payload = "INTENTIONAL_FAIL" if fail_tests else request.payload
        test_req = MaterialExecutionRequest(**{**asdict(request), "payload": test_payload})
        test_ref, tests_ok = self._provider.run_tests(test_req, path)
        state = EffectState.EVIDENCE_READY if tests_ok else EffectState.RECONCILED_FAILURE
        outcome = Outcome.SUCCEEDED if tests_ok else Outcome.FAILED
        self._record(request, state, str(path), digest,
                     {"outcome": outcome.value, "test_execution_ref": test_ref}, pre_version)
        return self._result(
            request, started, outcome, state,
            artifact=str(path), digest=digest, readback=observed, test_ref=test_ref,
            failure=None if tests_ok else "tests_failed",
        )

    def reconcile(self, request: MaterialExecutionRequest) -> MaterialExecutionResult:
        existing = self._store.get(request.effect_id)
        if existing is None:
            return self.execute(request)
        return self._replay(request, existing, time.time())

    def restart(self) -> MaterialPlane:
        return MaterialPlane(
            store=DurableEffectStore(self._store.path),
            provider=FilesystemMaterialProvider(self._provider.root),
            boundary=self._boundary,
            live_generation=self._generation,
        )

    def _recover_orphan(self, request, existing, started) -> MaterialExecutionResult:
        path = self._provider.artifact_path(request.bound_object)
        expected = existing["content_hash"] or sha256(request.payload.encode()).hexdigest()
        observed = self._provider.readback(request, expected)
        if observed.reconciliation is Reconciliation.ABSENT:
            return self._result(
                request, started, Outcome.EXECUTION_UNKNOWN, EffectState.EXECUTION_UNKNOWN,
                failure="orphan_effect_absent", replayed=True,
            )
        if observed.reconciliation is Reconciliation.MATCH:
            test_ref, tests_ok = self._provider.run_tests(request, path)
            state = EffectState.EVIDENCE_READY if tests_ok else EffectState.RECONCILED_FAILURE
            outcome = Outcome.SUCCEEDED if tests_ok else Outcome.FAILED
            self._record(
                request, state, str(path), expected,
                {"outcome": outcome.value, "test_execution_ref": test_ref},
                existing["pre_effect_version"] or INITIAL_OBJECT_VERSION,
            )
            return self._result(
                request, started, outcome, state,
                artifact=str(path), digest=expected, readback=observed, test_ref=test_ref,
                failure=None if tests_ok else "tests_failed", replayed=True,
            )
        return self._result(
            request, started, Outcome.FAILED, EffectState.MATERIAL_DRIFT,
            artifact=str(path) if path.exists() else "", digest=expected,
            readback=observed, failure="orphan_effect_mismatch", replayed=True,
        )

    def _replay(self, request, existing, started) -> MaterialExecutionResult:
        persisted_identity = existing["request_identity"] or ""
        if persisted_identity and persisted_identity != request.identity_digest():
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED,
                                failure="effect_identity_conflict", replayed=False)
        receipt = json.loads(existing["receipt"] or "{}")
        state_name = existing["state"] or EffectState.UNKNOWN.value
        outcome_name = receipt.get("outcome")
        if state_name in NONTERMINAL_STATES or not outcome_name:
            return self._recover_orphan(request, existing, started)
        digest = existing["content_hash"] or ""
        observed = self._provider.readback(request, digest) if existing["artifact"] else None
        if observed is not None and observed.reconciliation != Reconciliation.MATCH:
            return self._result(
                request, started, Outcome.FAILED, EffectState.MATERIAL_DRIFT,
                artifact=existing["artifact"] or "", digest=digest, readback=observed,
                failure="material_drift", replayed=True,
            )
        return self._result(
            request, started,
            Outcome(outcome_name),
            EffectState(state_name),
            artifact=existing["artifact"] or "", digest=digest, readback=observed,
            test_ref=receipt.get("test_execution_ref", ""), replayed=True,
        )

    def _record(self, request, state, artifact, digest, receipt, pre_version) -> None:
        self._store.put(
            effect_id=request.effect_id,
            logical_operation_id=request.logical_operation_id,
            generation=request.generation,
            state=state.value,
            payload=request.payload,
            artifact=artifact,
            content_hash=digest,
            receipt=json.dumps(receipt),
            request_identity=request.identity_digest(),
            expected_version=request.expected_object_version,
            pre_effect_version=pre_version,
        )

    def _result(self, request, started, outcome, state, *,
                artifact="", digest="", readback=None, test_ref="",
                unknown_at=None, failure=None, replayed=False) -> MaterialExecutionResult:
        return MaterialExecutionResult(
            operation_id=request.logical_operation_id,
            effect_id=request.effect_id,
            provider_identity=self._provider.identity,
            started_at=started,
            completed_at=None if outcome is Outcome.EXECUTION_UNKNOWN else time.time(),
            unknown_at=unknown_at,
            outcome=outcome,
            state=state,
            material_artifact_ref=artifact,
            observed_object_version=digest[:12],
            execution_hash=digest,
            test_execution_ref=test_ref,
            raw_receipt_ref=request.effect_id,
            readback=readback,
            replayed=replayed,
            promoted=False,
            failure=failure,
            material=bool(artifact),
            authority_ref_validated=AUTHORITY_REF_VALIDATED,
        )
