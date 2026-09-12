from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from .governed_execution import GovernedSoftwareExecutionResult


class ObservationEvidenceStateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class EffectObservation:
    mission_id: str
    capability_id: str
    ocs_id: str
    governed_execution_receipt: str
    execution_status: str
    observed_effect: Mapping[str, object]

    def validate(self) -> None:
        for field in ("mission_id", "capability_id", "ocs_id", "governed_execution_receipt", "execution_status"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ObservationEvidenceStateError(f"observation_{field}_required")
        if not self.observed_effect:
            raise ObservationEvidenceStateError("observation_effect_required")


@dataclass(frozen=True, slots=True)
class EvidenceReceipt:
    mission_id: str
    capability_id: str
    ocs_id: str
    governed_execution_receipt: str
    execution_status: str
    observation_hash: str
    evidence_receipt: str


@dataclass(frozen=True, slots=True)
class InstitutionalStateSnapshot:
    mission_id: str
    previous_state_hash: str
    evidence_receipt: str
    state_version: int
    state: Mapping[str, object]
    state_hash: str


@dataclass(frozen=True, slots=True)
class ObservationEvidenceStateResult:
    observation: EffectObservation
    evidence: EvidenceReceipt
    state_snapshot: InstitutionalStateSnapshot


class InstitutionalStateStore:
    """Narrow COI11 state abstraction. Durable/distributed persistence is a later concern."""

    def __init__(self) -> None:
        self._state: dict[str, InstitutionalStateSnapshot] = {}
        self._consumed_execution_receipts: set[str] = set()

    def current(self, mission_id: str) -> InstitutionalStateSnapshot | None:
        return self._state.get(mission_id)

    def has_consumed(self, governed_execution_receipt: str) -> bool:
        return governed_execution_receipt in self._consumed_execution_receipts

    def commit(self, snapshot: InstitutionalStateSnapshot, governed_execution_receipt: str) -> None:
        if governed_execution_receipt in self._consumed_execution_receipts:
            raise ObservationEvidenceStateError("evidence_execution_receipt_replay")
        self._state[snapshot.mission_id] = snapshot
        self._consumed_execution_receipts.add(governed_execution_receipt)


class ObservationEvidenceStateUpdater:
    """COI11: qualify observed effects, emit evidence, and update mission state atomically."""

    _SUCCESS_STATUSES = frozenset({"EXECUTED", "EXECUTED_CONFIRMED", "SUCCESS"})

    def __init__(self, *, state_store: InstitutionalStateStore) -> None:
        self._state_store = state_store

    def qualify_and_update(
        self,
        *,
        execution: GovernedSoftwareExecutionResult,
        observation: EffectObservation,
        state_delta: Mapping[str, object],
    ) -> ObservationEvidenceStateResult:
        observation.validate()
        if execution.mission_id != observation.mission_id:
            raise ObservationEvidenceStateError("evidence_mission_mismatch")
        if execution.capability_id != observation.capability_id:
            raise ObservationEvidenceStateError("evidence_capability_mismatch")
        if execution.ocs_id != observation.ocs_id:
            raise ObservationEvidenceStateError("evidence_ocs_mismatch")
        if execution.governed_execution_receipt != observation.governed_execution_receipt:
            raise ObservationEvidenceStateError("evidence_execution_receipt_mismatch")
        if execution.execution_status != observation.execution_status:
            raise ObservationEvidenceStateError("evidence_execution_status_mismatch")
        if observation.execution_status not in self._SUCCESS_STATUSES:
            raise ObservationEvidenceStateError("evidence_unqualified_execution_status")
        if self._state_store.has_consumed(observation.governed_execution_receipt):
            raise ObservationEvidenceStateError("evidence_execution_receipt_replay")
        if not state_delta:
            raise ObservationEvidenceStateError("state_delta_required")

        observation_hash = self._digest({
            "mission_id": observation.mission_id,
            "capability_id": observation.capability_id,
            "ocs_id": observation.ocs_id,
            "governed_execution_receipt": observation.governed_execution_receipt,
            "execution_status": observation.execution_status,
            "observed_effect": dict(observation.observed_effect),
        })
        evidence_receipt = self._digest({
            "observation_hash": observation_hash,
            "adapter_execution_receipt": execution.adapter_execution_receipt.execution_receipt,
            "governed_execution_receipt": execution.governed_execution_receipt,
        })
        evidence = EvidenceReceipt(
            mission_id=observation.mission_id,
            capability_id=observation.capability_id,
            ocs_id=observation.ocs_id,
            governed_execution_receipt=observation.governed_execution_receipt,
            execution_status=observation.execution_status,
            observation_hash=observation_hash,
            evidence_receipt=evidence_receipt,
        )

        previous = self._state_store.current(observation.mission_id)
        previous_hash = previous.state_hash if previous else "GENESIS"
        previous_state = dict(previous.state) if previous else {}
        new_state = {**previous_state, **dict(state_delta)}
        version = previous.state_version + 1 if previous else 1
        state_hash = self._digest({
            "mission_id": observation.mission_id,
            "previous_state_hash": previous_hash,
            "evidence_receipt": evidence_receipt,
            "state_version": version,
            "state": new_state,
        })
        snapshot = InstitutionalStateSnapshot(
            mission_id=observation.mission_id,
            previous_state_hash=previous_hash,
            evidence_receipt=evidence_receipt,
            state_version=version,
            state=new_state,
            state_hash=state_hash,
        )
        self._state_store.commit(snapshot, observation.governed_execution_receipt)
        return ObservationEvidenceStateResult(observation, evidence, snapshot)

    @staticmethod
    def _digest(payload: object) -> str:
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()
