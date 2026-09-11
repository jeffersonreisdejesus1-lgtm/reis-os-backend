from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from .contracts import (
    Candidate,
    MemoryLevel,
    MemoryRecord,
    NMState,
    OperationalCommitContext,
    PredictionResidual,
    validate_memory_promotion,
)
from .runtime import CognitivePhysiologyRuntime


@dataclass(frozen=True)
class ExpectedOutcome:
    expected_observation: Mapping[str, object] = field(default_factory=dict)
    expected_effect: Mapping[str, object] = field(default_factory=dict)
    expected_state_delta: Mapping[str, object] = field(default_factory=dict)
    expected_latency_ms: int | None = None
    expected_failure_modes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObservedOutcome:
    observation: Mapping[str, object] = field(default_factory=dict)
    effect: Mapping[str, object] = field(default_factory=dict)
    state_delta: Mapping[str, object] = field(default_factory=dict)
    latency_ms: int | None = None
    failure_mode: str | None = None


@dataclass(frozen=True)
class CompetitionResult:
    winner_id: str
    ranked_ids: tuple[str, ...]
    scores: Mapping[str, float]


@dataclass(frozen=True)
class CognitiveCycleResult:
    winner: Candidate
    competition: CompetitionResult
    effect_result: object | None
    residual: PredictionResidual
    nm_state: NMState
    episodic_record: MemoryRecord


class LocalMemoryStore:
    """OCS-local memory with explicit M2->M3 qualification boundary."""

    def __init__(self, *, ocs_id: str) -> None:
        self.ocs_id = ocs_id
        self._records: dict[MemoryLevel, dict[str, MemoryRecord]] = {
            level: {} for level in MemoryLevel
        }

    def put(self, record: MemoryRecord) -> None:
        record.validate()
        if record.ocs_id != self.ocs_id:
            raise PermissionError("cross_ocs_memory_write_denied")
        self._records[record.level][record.record_id] = record

    def get(self, level: MemoryLevel, record_id: str) -> MemoryRecord:
        return self._records[level][record_id]

    def consolidate(
        self,
        *,
        source_record_id: str,
        target_record_id: str,
        qualified: bool,
        persistence_authorized: bool,
        generation: int,
    ) -> MemoryRecord:
        validate_memory_promotion(
            MemoryLevel.M2,
            MemoryLevel.M3,
            qualified=qualified,
        )
        if not persistence_authorized:
            raise PermissionError("m3_persistence_authority_required")
        source = self.get(MemoryLevel.M2, source_record_id)
        target = MemoryRecord(
            record_id=target_record_id,
            ocs_id=self.ocs_id,
            level=MemoryLevel.M3,
            generation=generation,
            provenance_ref=source.provenance_ref,
            mission_id=source.mission_id,
            payload={
                "derived_from": source.record_id,
                "qualified_payload": dict(source.payload),
            },
        )
        self.put(target)
        return target


class UniversalCognitiveEngine:
    """Deterministic universal slice around an authority-neutral OCS runtime."""

    def __init__(self, runtime: CognitivePhysiologyRuntime) -> None:
        self.runtime = runtime
        self.memory = LocalMemoryStore(ocs_id=runtime.ocs_id)

    @staticmethod
    def score(candidate: Candidate) -> float:
        candidate.validate()
        evidence_bonus = min(len(candidate.evidence_refs), 3) * 0.05
        return (
            0.25 * candidate.salience
            + 0.20 * candidate.novelty
            + 0.20 * candidate.confidence
            + 0.15 * (1.0 - candidate.uncertainty)
            + evidence_bonus
            - 0.25 * candidate.risk
        )

    def compete(self, candidates: Iterable[Candidate]) -> CompetitionResult:
        candidate_list = list(candidates)
        if not candidate_list:
            raise ValueError("competition_requires_candidates")
        scores = {
            candidate.candidate_id: self.score(candidate)
            for candidate in candidate_list
        }
        ranked = tuple(
            sorted(
                scores,
                key=lambda candidate_id: (-scores[candidate_id], candidate_id),
            )
        )
        return CompetitionResult(
            winner_id=ranked[0],
            ranked_ids=ranked,
            scores=scores,
        )

    @staticmethod
    def compare(
        expected: ExpectedOutcome,
        observed: ObservedOutcome,
    ) -> PredictionResidual:
        def mismatch(
            left: Mapping[str, object],
            right: Mapping[str, object],
        ) -> float:
            keys = set(left) | set(right)
            if not keys:
                return 0.0
            mismatches = sum(left.get(key) != right.get(key) for key in keys)
            return mismatches / len(keys)

        temporal = 0.0
        if (
            expected.expected_latency_ms is not None
            and observed.latency_ms is not None
        ):
            denominator = max(expected.expected_latency_ms, 1)
            temporal = min(
                abs(observed.latency_ms - expected.expected_latency_ms)
                / denominator,
                1.0,
            )

        unexpected_failure = (
            observed.failure_mode is not None
            and observed.failure_mode not in expected.expected_failure_modes
        )
        risk = 1.0 if unexpected_failure else 0.0
        return PredictionResidual(
            semantic=mismatch(
                expected.expected_observation,
                observed.observation,
            ),
            goal=mismatch(expected.expected_effect, observed.effect),
            causal=mismatch(
                expected.expected_state_delta,
                observed.state_delta,
            ),
            temporal=temporal,
            calibration=0.0,
            risk=risk,
            tool_behavior=mismatch(expected.expected_effect, observed.effect),
            environment=mismatch(
                expected.expected_observation,
                observed.observation,
            ),
        )

    @staticmethod
    def modulate(winner: Candidate, residual: PredictionResidual) -> NMState:
        residual_values = residual.as_mapping().values()
        residual_mean = sum(residual_values) / len(residual.as_mapping())
        state = NMState(
            salience=winner.salience,
            novelty=winner.novelty,
            uncertainty=winner.uncertainty,
            confidence=winner.confidence,
            risk=max(winner.risk, residual.risk),
            prediction_error=min(max(residual_mean, 0.0), 1.0),
            cognitive_load=min(0.5 + winner.uncertainty * 0.5, 1.0),
            exploration_drive=winner.novelty,
            exploitation_drive=winner.confidence,
            urgency=max(winner.salience, winner.risk),
            resource_pressure=0.0,
        )
        state.validate()
        return state

    def run_cycle(
        self,
        *,
        mission_id: str,
        candidates: Iterable[Candidate],
        expected: ExpectedOutcome,
        observe: Callable[[], ObservedOutcome],
        generation: int,
        action_effect_id: str | None = None,
        action: Callable[[], object] | None = None,
        commit_context: OperationalCommitContext | None = None,
        provenance_ref: str,
    ) -> CognitiveCycleResult:
        self.runtime.assert_generation(generation)
        candidate_list = list(candidates)
        competition = self.compete(candidate_list)
        by_id = {
            candidate.candidate_id: candidate
            for candidate in candidate_list
        }
        winner = by_id[competition.winner_id]

        for candidate in candidate_list:
            self.runtime.ingest_candidate(candidate, generation=generation)
        self.runtime.cognitive_ignition(
            winner.candidate_id,
            generation=generation,
        )

        effect_result: object | None = None
        if action is not None:
            if action_effect_id is None or commit_context is None:
                raise PermissionError(
                    "material_action_requires_explicit_operational_commit"
                )
            effect_result = self.runtime.operational_commit(
                effect_id=action_effect_id,
                context=commit_context,
                generation=generation,
                effect=action,
            )

        observed = observe()
        residual = self.compare(expected, observed)
        nm_state = self.modulate(winner, residual)
        episodic = MemoryRecord(
            record_id=(
                f"episode:{mission_id}:{winner.candidate_id}:{generation}"
            ),
            ocs_id=self.runtime.ocs_id,
            level=MemoryLevel.M2,
            generation=generation,
            provenance_ref=provenance_ref,
            mission_id=mission_id,
            payload={
                "winner_id": winner.candidate_id,
                "ranked_ids": competition.ranked_ids,
                "residual": residual.as_mapping(),
                "effect_executed": action is not None,
            },
        )
        self.memory.put(episodic)
        return CognitiveCycleResult(
            winner=winner,
            competition=competition,
            effect_result=effect_result,
            residual=residual,
            nm_state=nm_state,
            episodic_record=episodic,
        )
