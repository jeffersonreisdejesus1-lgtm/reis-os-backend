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


@dataclass(frozen=True, slots=True)
class MaterialReadback:
    effect_id: str
    source: str
    observed_object_version: str
    observed_hash: str
    observed_state: str
    timestamp: float
    reconciliation: Reconciliation


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
                receipt TEXT
                )"""
            )

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
            conn.execute(f"INSERT OR REPLACE INTO effects ({keys}) VALUES ({marks})", tuple(fields.values()))


class FilesystemMaterialProvider:
    """Program-isolated provider. Writes a bound file and reads it back."""

    identity = "filesystem-fixture-provider"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def artifact_path(self, bound_object: str) -> Path:
        safe = bound_object.replace("://", "_").replace("/", "_")
        return self.root / f"{safe}.txt"

    def apply(self, request: MaterialExecutionRequest) -> tuple[Path, str]:
        path = self.artifact_path(request.bound_object)
        path.write_text(request.payload, encoding="utf-8")
        digest = sha256(path.read_bytes()).hexdigest()
        return path, digest

    def readback(self, request: MaterialExecutionRequest, expected_hash: str) -> MaterialReadback:
        path = self.artifact_path(request.bound_object)
        if not path.exists():
            return MaterialReadback(
                request.effect_id, str(path), "", "", "ABSENT", time.time(), Reconciliation.ABSENT
            )
        observed = path.read_text(encoding="utf-8")
        digest = sha256(observed.encode()).hexdigest()
        match = digest == expected_hash and observed == request.payload
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
        probe.write_text(
            "from pathlib import Path\n"
            f"p = Path({str(artifact)!r})\n"
            f"assert p.read_text(encoding='utf-8') == {request.payload!r}\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            [sys.executable, str(probe)], capture_output=True, text=True, check=False
        )
        ref = f"proc:{completed.returncode}:{sha256(completed.stdout.encode()).hexdigest()[:12]}"
        return ref, completed.returncode == 0


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
        auth = self._boundary.decide(actor=request.actor, kind=MutationKind.EDIT_FILE)
        if not auth.allowed:
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED, failure=auth.reason)
        if request.generation != self._generation:
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED, failure="stale_generation")
        if request.capability in {"GITHUB_MERGE_PR", "FOUNDER_PROMOTION", "GATE_PROMOTION"}:
            return self._result(request, started, Outcome.FAILED, EffectState.DENIED, failure="authority_expansion_denied")
        if not provider_available:
            return self._result(request, started, Outcome.FAILED, EffectState.HOLD, failure="provider_unavailable")

        existing = self._store.get(request.effect_id)
        if existing is not None:
            receipt = json.loads(existing["receipt"] or "{}")
            return MaterialExecutionResult(
                operation_id=request.logical_operation_id,
                effect_id=request.effect_id,
                provider_identity=self._provider.identity,
                started_at=started,
                completed_at=time.time(),
                unknown_at=None,
                outcome=Outcome(receipt.get("outcome", Outcome.SUCCEEDED)),
                state=EffectState(existing["state"]),
                material_artifact_ref=existing["artifact"] or "",
                observed_object_version=existing["content_hash"][:12] if existing["content_hash"] else "",
                execution_hash=existing["content_hash"] or "",
                test_execution_ref=receipt.get("test_execution_ref", ""),
                raw_receipt_ref=existing["effect_id"],
                readback=None,
                replayed=True,
                promoted=False,
                failure=None,
                material=True,
            )

        if pretick_timeout:
            self._store.put(
                effect_id=request.effect_id,
                logical_operation_id=request.logical_operation_id,
                generation=request.generation,
                state=EffectState.EXECUTION_UNKNOWN.value,
                payload=request.payload,
                artifact="",
                content_hash="",
                receipt=json.dumps({"outcome": Outcome.EXECUTION_UNKNOWN.value}),
            )
            return self._result(
                request, started, Outcome.EXECUTION_UNKNOWN, EffectState.EXECUTION_UNKNOWN,
                unknown_at=time.time(), failure="timeout_before_known_effect"
            )

        self._store.put(
            effect_id=request.effect_id,
            logical_operation_id=request.logical_operation_id,
            generation=request.generation,
            state=EffectState.EXECUTING.value,
            payload=request.payload,
            artifact="",
            content_hash="",
            receipt="{}",
        )
        path, digest = self._provider.apply(request)
        if post_effect_unknown:
            self._store.put(
                effect_id=request.effect_id,
                logical_operation_id=request.logical_operation_id,
                generation=request.generation,
                state=EffectState.EXECUTION_UNKNOWN.value,
                payload=request.payload,
                artifact=str(path),
                content_hash=digest,
                receipt=json.dumps({"outcome": Outcome.EXECUTION_UNKNOWN.value}),
            )
            return self._result(
                request, started, Outcome.EXECUTION_UNKNOWN, EffectState.RECONCILING,
                artifact=str(path), digest=digest, unknown_at=time.time(),
                failure="timeout_after_potential_effect",
            )

        observed = self._provider.readback(request, digest)
        if observed.reconciliation != Reconciliation.MATCH:
            self._store.put(
                effect_id=request.effect_id,
                logical_operation_id=request.logical_operation_id,
                generation=request.generation,
                state=EffectState.RECONCILED_FAILURE.value,
                payload=request.payload,
                artifact=str(path),
                content_hash=digest,
                receipt=json.dumps({"outcome": Outcome.FAILED.value}),
            )
            return self._result(
                request, started, Outcome.FAILED, EffectState.RECONCILED_FAILURE,
                artifact=str(path), digest=digest, readback=observed, failure="readback_mismatch"
            )

        payload_for_test = "INTENTIONAL_FAIL" if fail_tests else request.payload
        test_req = MaterialExecutionRequest(**{**asdict(request), "payload": payload_for_test})
        test_ref, tests_ok = self._provider.run_tests(test_req, path)
        if not tests_ok:
            self._persist_ready(request, path, digest, test_ref, EffectState.RECONCILED_FAILURE, Outcome.FAILED)
            return self._result(
                request, started, Outcome.FAILED, EffectState.RECONCILED_FAILURE,
                artifact=str(path), digest=digest, readback=observed,
                test_ref=test_ref, failure="tests_failed"
            )
        self._persist_ready(request, path, digest, test_ref, EffectState.EVIDENCE_READY, Outcome.SUCCEEDED)
        return self._result(
            request, started, Outcome.SUCCEEDED, EffectState.EVIDENCE_READY,
            artifact=str(path), digest=digest, readback=observed, test_ref=test_ref,
        )

    def reconcile(self, request: MaterialExecutionRequest) -> MaterialExecutionResult:
        existing = self._store.get(request.effect_id)
        if existing is None:
            return self.execute(request)
        if existing["artifact"]:
            observed = self._provider.readback(request, existing["content_hash"] or "")
            if observed.reconciliation == Reconciliation.MATCH:
                return self._result(
                    request, time.time(), Outcome.SUCCEEDED, EffectState.RECONCILED_SUCCESS,
                    artifact=existing["artifact"], digest=existing["content_hash"] or "",
                    readback=observed,
                )
            if observed.reconciliation == Reconciliation.ABSENT:
                return self.execute(request)
            return self._result(
                request, time.time(), Outcome.FAILED, EffectState.RECONCILED_FAILURE,
                artifact=existing["artifact"], digest=existing["content_hash"] or "",
                readback=observed, failure="reconcile_mismatch",
            )
        return self._result(
            request, time.time(), Outcome.EXECUTION_UNKNOWN, EffectState.UNKNOWN,
            failure="reconcile_still_unknown",
        )

    def restart(self) -> MaterialPlane:
        return MaterialPlane(
            store=self._store,
            provider=self._provider,
            boundary=self._boundary,
            live_generation=self._generation,
        )

    def _persist_ready(self, request, path, digest, test_ref, state, outcome) -> None:
        self._store.put(
            effect_id=request.effect_id,
            logical_operation_id=request.logical_operation_id,
            generation=request.generation,
            state=state.value,
            payload=request.payload,
            artifact=str(path),
            content_hash=digest,
            receipt=json.dumps({"outcome": outcome.value, "test_execution_ref": test_ref}),
        )

    def _result(self, request, started, outcome, state, *,
                artifact="", digest="", readback=None, test_ref="",
                unknown_at=None, failure=None) -> MaterialExecutionResult:
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
            replayed=False,
            promoted=False,
            failure=failure,
            material=True,
        )
