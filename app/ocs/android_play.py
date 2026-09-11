from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any


OCS_ID = "REISOS::INST::ANDROID_PLAY::001"
CANONICAL_NAME = "ANDROID PLAY STEWARDSHIP"
NAMESPACE = "reisos/android-play"


class Disposition(str, Enum):
    PASS_CANDIDATE = "PASS_CANDIDATE"
    HOLD = "HOLD"
    REMEDIATION_REQUIRED = "REMEDIATION_REQUIRED"
    DENY = "DENY"


class CognitiveMode(str, Enum):
    FAST = "FAST"
    DELIBERATIVE = "DELIBERATIVE"
    RECOVERY = "RECOVERY"
    CONSOLIDATION = "CONSOLIDATION"


@dataclass(frozen=True)
class AuthorityEnvelope:
    may_investigate_official_sources: bool = True
    may_assess_readiness: bool = True
    may_issue_specialty_disposition: bool = True
    may_publish_production: bool = False
    may_change_price: bool = False
    may_self_promote: bool = False
    may_expand_authority: bool = False


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source_url: str
    source_kind: str
    retrieved_at: datetime
    effective_from: date | None
    expires_at: datetime | None
    content_hash: str
    claim: str

    def is_fresh(self, now: datetime) -> bool:
        return self.expires_at is None or now <= self.expires_at


@dataclass
class MemoryModel:
    working: dict[str, Any] = field(default_factory=dict)
    episodic: list[dict[str, Any]] = field(default_factory=list)
    semantic: dict[str, Any] = field(default_factory=dict)
    procedural: dict[str, Any] = field(default_factory=dict)


@dataclass
class CognitiveState:
    mission_id: str
    mode: CognitiveMode = CognitiveMode.FAST
    goal: str = ""
    expected_state: dict[str, Any] = field(default_factory=dict)
    observed_state: dict[str, Any] = field(default_factory=dict)
    prediction_error: float = 0.0
    salience: float = 0.0
    novelty: float = 0.0
    uncertainty: float = 0.0
    confidence: float = 1.0
    risk: float = 0.0
    cognitive_load: float = 0.0
    generation: int = 1
    sequence: int = 0


@dataclass
class RuntimeSnapshot:
    state: CognitiveState
    memory: MemoryModel
    evidence: dict[str, EvidenceRecord]


@dataclass
class RuntimeEvent:
    event_type: str
    payload: dict[str, Any]
    sequence: int
    generation: int
    observed_at: datetime


class AndroidPlayOCS:
    """Material runtime for the Android / Google Play specialty OCS.

    R1: state/workspace
    R2: progress + prediction error
    R3: typed transitions
    R4: physiological scheduling
    R5: telemetry
    R6: constitutional/policy checks
    R7: specialized governance execution
    """

    ocs_id = OCS_ID
    canonical_name = CANONICAL_NAME
    namespace = NAMESPACE

    def __init__(self, mission_id: str) -> None:
        if not mission_id.strip():
            raise ValueError("mission_id is required")
        self.authority = AuthorityEnvelope()
        self.state = CognitiveState(mission_id=mission_id)
        self.memory = MemoryModel()
        self.evidence: dict[str, EvidenceRecord] = {}
        self.telemetry: list[RuntimeEvent] = []
        self._transition_types = {
            "SENSE",
            "MODEL",
            "PREDICT",
            "COMPARE",
            "MODULATE",
            "COMPETE",
            "GATE",
            "BROADCAST",
            "SPECIALIST_PROCESS",
            "ACT",
            "OBSERVE",
            "UPDATE",
            "LEARN_CANDIDATE",
            "CONSOLIDATE",
            "HOMEOSTASIS",
            "RECOVER",
        }

    # R5
    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.state.sequence += 1
        self.telemetry.append(
            RuntimeEvent(
                event_type=event_type,
                payload=payload,
                sequence=self.state.sequence,
                generation=self.state.generation,
                observed_at=datetime.now(timezone.utc),
            )
        )

    # R3
    def transition(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if event_type not in self._transition_types:
            raise ValueError(f"unknown transition type: {event_type}")
        self._emit(event_type, payload or {})

    # Evidence organ
    def register_evidence(
        self,
        *,
        evidence_id: str,
        source_url: str,
        source_kind: str,
        claim: str,
        raw_content: str,
        effective_from: date | None = None,
        expires_at: datetime | None = None,
        retrieved_at: datetime | None = None,
    ) -> EvidenceRecord:
        if not evidence_id or not source_url.startswith("https://"):
            raise ValueError("evidence_id and https source_url are required")
        if source_kind not in {"ANDROID_OFFICIAL", "GOOGLE_PLAY_OFFICIAL"}:
            raise PermissionError("non-official source cannot enter canonical policy ledger")
        record = EvidenceRecord(
            evidence_id=evidence_id,
            source_url=source_url,
            source_kind=source_kind,
            retrieved_at=retrieved_at or datetime.now(timezone.utc),
            effective_from=effective_from,
            expires_at=expires_at,
            content_hash=sha256(raw_content.encode("utf-8")).hexdigest(),
            claim=claim,
        )
        self.evidence[evidence_id] = record
        self._emit("UPDATE", {"evidence_id": evidence_id, "hash": record.content_hash})
        return record

    # R6
    def constitutional_precheck(self, action: str, *, authorized: bool) -> None:
        prohibited = {
            "PUBLISH_PRODUCTION",
            "CHANGE_PRICE",
            "SELF_PROMOTE",
            "EXPAND_AUTHORITY",
            "USE_PERMANENT_CREDENTIALS",
        }
        if action in prohibited:
            raise PermissionError(f"reserved or prohibited action: {action}")
        if not authorized:
            raise PermissionError("explicit authorization required")

    def policy_freshness_gate(
        self, required_evidence_ids: list[str], *, now: datetime | None = None
    ) -> None:
        current = now or datetime.now(timezone.utc)
        missing = [eid for eid in required_evidence_ids if eid not in self.evidence]
        stale = [
            eid
            for eid in required_evidence_ids
            if eid in self.evidence and not self.evidence[eid].is_fresh(current)
        ]
        if missing or stale:
            raise RuntimeError(f"policy evidence gate failed: missing={missing}, stale={stale}")

    # R4
    def schedule_mode(self) -> CognitiveMode:
        if self.state.risk >= 0.7 or self.state.uncertainty >= 0.5:
            self.state.mode = CognitiveMode.DELIBERATIVE
        elif self.state.cognitive_load >= 0.9:
            self.state.mode = CognitiveMode.RECOVERY
        else:
            self.state.mode = CognitiveMode.FAST
        self._emit("GATE", {"mode": self.state.mode.value})
        return self.state.mode

    # R2
    def compare_prediction(self, observed: dict[str, Any]) -> float:
        self.state.observed_state = dict(observed)
        expected = self.state.expected_state
        keys = set(expected) | set(observed)
        if not keys:
            error = 0.0
        else:
            mismatches = sum(expected.get(k) != observed.get(k) for k in keys)
            error = mismatches / len(keys)
        self.state.prediction_error = error
        self.state.confidence = max(0.0, min(1.0, 1.0 - error))
        self._emit("COMPARE", {"prediction_error": error})
        return error

    # R1 + recurrent cognitive loop
    def recurrent_cycle(
        self,
        *,
        sensory_input: dict[str, Any],
        prediction: dict[str, Any],
        candidates: list[dict[str, Any]],
        authorized: bool,
    ) -> dict[str, Any]:
        self.constitutional_precheck("COGNITIVE_CYCLE", authorized=authorized)
        self.transition("SENSE", sensory_input)
        self.memory.working["sensory_input"] = dict(sensory_input)
        self.transition("MODEL", {"keys": sorted(sensory_input)})
        self.state.expected_state = dict(prediction)
        self.transition("PREDICT", prediction)

        self.state.novelty = float(sensory_input.get("novelty", 0.0))
        self.state.uncertainty = float(sensory_input.get("uncertainty", 0.0))
        self.state.risk = float(sensory_input.get("risk", 0.0))
        self.state.cognitive_load = float(sensory_input.get("cognitive_load", 0.0))
        self.state.salience = max(
            self.state.novelty, self.state.uncertainty, self.state.risk
        )
        self.transition("MODULATE", {"salience": self.state.salience})
        self.schedule_mode()

        ranked = sorted(
            candidates,
            key=lambda c: (
                float(c.get("goal_relevance", 0.0))
                + float(c.get("evidence_strength", 0.0))
                + float(c.get("salience", 0.0))
                + float(c.get("expected_value", 0.0))
                - float(c.get("risk", 0.0))
                - float(c.get("cost", 0.0))
            ),
            reverse=True,
        )
        winner = ranked[0] if ranked else None
        self.transition("COMPETE", {"candidate_count": len(ranked)})
        self.memory.working["workspace_winner"] = winner
        self.transition("BROADCAST", {"winner": winner})
        self.transition("SPECIALIST_PROCESS", {"mode": self.state.mode.value})

        observed = dict(sensory_input.get("observed_state", {}))
        error = self.compare_prediction(observed)
        self.transition("UPDATE", {"prediction_error": error})
        self.memory.episodic.append(
            {
                "sequence": self.state.sequence,
                "input": dict(sensory_input),
                "prediction": dict(prediction),
                "winner": winner,
                "prediction_error": error,
            }
        )
        self.transition("LEARN_CANDIDATE", {"episodic_index": len(self.memory.episodic) - 1})
        self.transition("HOMEOSTASIS", {"cognitive_load": self.state.cognitive_load})
        return {
            "ocs_id": self.ocs_id,
            "mode": self.state.mode.value,
            "winner": winner,
            "prediction_error": error,
            "confidence": self.state.confidence,
            "sequence": self.state.sequence,
        }

    def consolidate(self) -> int:
        self.state.mode = CognitiveMode.CONSOLIDATION
        consolidated = 0
        for episode in self.memory.episodic:
            if episode["prediction_error"] == 0.0 and episode["winner"] is not None:
                key = f"pattern:{consolidated}"
                self.memory.semantic[key] = episode["winner"]
                consolidated += 1
        self.transition("CONSOLIDATE", {"consolidated": consolidated})
        return consolidated

    # Recovery / fencing
    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            state=CognitiveState(**vars(self.state)),
            memory=MemoryModel(
                working=dict(self.memory.working),
                episodic=[dict(x) for x in self.memory.episodic],
                semantic=dict(self.memory.semantic),
                procedural=dict(self.memory.procedural),
            ),
            evidence=dict(self.evidence),
        )

    def restore(self, snapshot: RuntimeSnapshot) -> None:
        if snapshot.state.mission_id != self.state.mission_id:
            raise PermissionError("cross-mission restore forbidden")
        previous_generation = self.state.generation
        restored = CognitiveState(**vars(snapshot.state))
        restored.generation = max(previous_generation, snapshot.state.generation) + 1
        self.state = restored
        self.memory = snapshot.memory
        self.evidence = snapshot.evidence
        self._emit("RECOVER", {"generation": self.state.generation})

    def readiness_disposition(
        self,
        *,
        required_evidence_ids: list[str],
        unresolved_findings: list[str],
        now: datetime | None = None,
    ) -> Disposition:
        try:
            self.policy_freshness_gate(required_evidence_ids, now=now)
        except RuntimeError:
            return Disposition.HOLD
        if unresolved_findings:
            return Disposition.REMEDIATION_REQUIRED
        return Disposition.PASS_CANDIDATE
