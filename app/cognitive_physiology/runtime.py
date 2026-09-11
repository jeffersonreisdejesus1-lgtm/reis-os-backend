from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from .contracts import BudgetEnvelope, Candidate, OperationalCommitContext


@dataclass
class WorkspaceState:
    generation: int = 0
    candidates: dict[str, Candidate] = field(default_factory=dict)
    broadcast_ids: list[str] = field(default_factory=list)

    def add_candidate(self, candidate: Candidate) -> None:
        candidate.validate()
        self.candidates[candidate.candidate_id] = candidate

    def broadcast(self, candidate_id: str) -> Candidate:
        candidate = self.candidates[candidate_id]
        if candidate_id not in self.broadcast_ids:
            self.broadcast_ids.append(candidate_id)
        return candidate


@dataclass
class InstitutionalState:
    generation: int = 0
    values: dict[str, object] = field(default_factory=dict)
    committed_transition_ids: set[str] = field(default_factory=set)

    def commit(
        self,
        *,
        transition_id: str,
        expected_generation: int,
        changes: Mapping[str, object],
        authority_validated: bool,
        r6_validated: bool,
    ) -> int:
        if not authority_validated:
            raise PermissionError("institutional_commit_authority_required")
        if not r6_validated:
            raise PermissionError(
                "institutional_commit_r6_validation_required"
            )
        if transition_id in self.committed_transition_ids:
            return self.generation
        if expected_generation != self.generation:
            raise PermissionError("institutional_generation_mismatch")
        self.values.update(changes)
        self.committed_transition_ids.add(transition_id)
        self.generation += 1
        return self.generation


class CognitivePhysiologyRuntime:
    """Authority-neutral shared physiology.

    The runtime can host candidate generation/broadcast and enforce commit
    predicates. It never resolves or creates authority by itself.
    """

    def __init__(
        self,
        *,
        ocs_id: str,
        identity_ref: str,
        state_namespace: str,
        memory_namespace: str,
        generation: int = 0,
        budget: BudgetEnvelope | None = None,
    ) -> None:
        self.ocs_id = ocs_id
        self.identity_ref = identity_ref
        self.state_namespace = state_namespace
        self.memory_namespace = memory_namespace
        self.generation = generation
        self.budget = budget or BudgetEnvelope()
        self.budget.validate()
        self.workspace = WorkspaceState(generation=generation)
        self.world = InstitutionalState(generation=generation)
        self._cycles = 0
        self._executed_effect_ids: set[str] = set()

    def assert_generation(self, generation: int) -> None:
        if generation != self.generation:
            raise PermissionError("stale_generation_writer")

    def ingest_candidate(
        self,
        candidate: Candidate,
        *,
        generation: int,
    ) -> None:
        self.assert_generation(generation)
        if candidate.source_ocs != self.ocs_id:
            raise PermissionError(
                "foreign_candidate_requires_explicit_handoff"
            )
        if self._cycles >= self.budget.max_cycles:
            raise RuntimeError("cognitive_cycle_budget_exhausted")
        self.workspace.add_candidate(candidate)
        self._cycles += 1

    def cognitive_ignition(
        self,
        candidate_id: str,
        *,
        generation: int,
    ) -> Candidate:
        self.assert_generation(generation)
        return self.workspace.broadcast(candidate_id)

    def operational_commit(
        self,
        *,
        effect_id: str,
        context: OperationalCommitContext,
        generation: int,
        effect: Callable[[], object],
    ) -> object:
        self.assert_generation(generation)
        if not context.allowed:
            raise PermissionError("operational_commit_denied")
        if effect_id in self._executed_effect_ids:
            raise PermissionError("duplicate_effect_denied")
        result = effect()
        self._executed_effect_ids.add(effect_id)
        return result

    def institutional_commit(
        self,
        *,
        transition_id: str,
        expected_generation: int,
        changes: Mapping[str, object],
        authority_validated: bool,
        r6_validated: bool,
    ) -> int:
        previous_generation = self.world.generation
        new_generation = self.world.commit(
            transition_id=transition_id,
            expected_generation=expected_generation,
            changes=changes,
            authority_validated=authority_validated,
            r6_validated=r6_validated,
        )
        if new_generation > previous_generation:
            self._advance_generation(new_generation)
        return new_generation

    def _advance_generation(self, new_generation: int) -> None:
        if new_generation <= self.generation:
            raise ValueError("generation_must_advance")
        self.generation = new_generation
        self.workspace.generation = new_generation

    def recover_to_generation(self, *, restored_generation: int) -> None:
        if restored_generation < 0:
            raise ValueError("invalid_recovery_generation")
        next_generation = max(self.generation, restored_generation) + 1
        self.generation = next_generation
        self.workspace = WorkspaceState(generation=next_generation)
        self.world.generation = next_generation
        self._cycles = 0
