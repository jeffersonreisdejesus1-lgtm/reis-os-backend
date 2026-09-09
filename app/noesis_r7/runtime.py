from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from typing import Any

from app.noesis_r7.contracts import (
    CommandStatus,
    CommunicationEnvelope,
    FailurePoint,
    GovernorContract,
    GovernorLease,
    GovernanceCommand,
    GovernanceReceipt,
    GovernanceTask,
    LeaseStatus,
    R7InvariantError,
    RecoveryCheckpoint,
)
from app.noesis_r7.integration import R1R6IntegrationContract


FORBIDDEN_COMMANDS = frozenset(
    {
        "SELF_ASSURANCE",
        "SELF_PROMOTION",
        "CREATE_AUTHORITY",
        "BYPASS_FOUNDER_GATE",
        "CANONICAL_WRITE",
        "PRODUCTION",
        "MERGE",
        "FOUNDER_PROMOTION",
    }
)


class R7GovernanceRuntime:
    """Internal Nóesis R7 governance plane over unchanged canonical R1-R6.

    Governor contracts are functional interfaces. Registering a contract does not
    create a new OCS identity and does not grant authority. Material external
    effects are deliberately outside this runtime; R7 can only govern internal
    state proposals and return receipts suitable for later effect gates.
    """

    def __init__(
        self,
        *,
        mission_id: str,
        integration: R1R6IntegrationContract,
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        if not mission_id:
            raise ValueError("mission_id_required")
        integration.assert_compatible()
        self.mission_id = mission_id
        self.integration = integration
        self._state: dict[str, Any] = dict(initial_state or {})
        self._state_version = 0
        self._governors: dict[str, GovernorContract] = {}
        self._leases: dict[str, GovernorLease] = {}
        self._generation_by_governor: dict[str, int] = {}
        self._tasks: list[GovernanceTask] = []
        self._task_seq = 0
        self._receipts: list[GovernanceReceipt] = []
        self._idempotency: dict[str, tuple[str, GovernanceReceipt]] = {}
        self._communications: list[CommunicationEnvelope] = []
        self._checkpoints: dict[str, RecoveryCheckpoint] = {}
        self._failure_point = FailurePoint.NONE

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    @property
    def state_version(self) -> int:
        return self._state_version

    @property
    def state(self) -> dict[str, Any]:
        return dict(self._state)

    @property
    def receipts(self) -> tuple[GovernanceReceipt, ...]:
        return tuple(self._receipts)

    @property
    def communications(self) -> tuple[CommunicationEnvelope, ...]:
        return tuple(self._communications)

    def inject_failure(self, point: FailurePoint) -> None:
        self._failure_point = point

    def register_governor(self, contract: GovernorContract) -> None:
        if contract.governor_id in self._governors:
            if self._governors[contract.governor_id] != contract:
                raise R7InvariantError("GOVERNOR_CONTRACT_CONFLICT")
            return
        claimed = set(contract.owned_state_keys)
        for existing in self._governors.values():
            overlap = claimed.intersection(existing.owned_state_keys)
            if overlap:
                joined = ",".join(sorted(overlap))
                raise R7InvariantError(f"STATE_OWNERSHIP_CONFLICT:{joined}")
        self._governors[contract.governor_id] = contract
        self._generation_by_governor.setdefault(contract.governor_id, 1)

    def issue_lease(self, lease: GovernorLease) -> None:
        contract = self._require_governor(lease.governor_id)
        if lease.mission_id != self.mission_id:
            raise R7InvariantError("LEASE_MISSION_MISMATCH")
        if lease.authority_ref != contract.authority_ceiling_ref:
            raise R7InvariantError("LEASE_AUTHORITY_CEILING_MISMATCH")
        generation = self._generation_by_governor[lease.governor_id]
        if lease.generation != generation:
            raise R7InvariantError("LEASE_GENERATION_MISMATCH")
        existing = self._leases.get(lease.lease_id)
        if existing is not None and existing != lease:
            raise R7InvariantError("LEASE_ID_CONFLICT")
        self._leases[lease.lease_id] = lease

    def fence_generation(self, governor_id: str) -> int:
        self._require_governor(governor_id)
        current = self._generation_by_governor[governor_id]
        for lease_id, lease in tuple(self._leases.items()):
            if lease.governor_id == governor_id and lease.generation == current:
                self._leases[lease_id] = replace(
                    lease,
                    status=LeaseStatus.FENCED,
                )
        self._generation_by_governor[governor_id] = current + 1
        return current + 1

    def current_generation(self, governor_id: str) -> int:
        self._require_governor(governor_id)
        return self._generation_by_governor[governor_id]

    def schedule(self, task: GovernanceTask) -> None:
        contract = self._require_governor(task.governor_id)
        if task.mission_id != self.mission_id:
            raise R7InvariantError("TASK_MISSION_MISMATCH")
        if task.command_type not in contract.allowed_commands:
            raise R7InvariantError("TASK_COMMAND_NOT_ALLOWED")
        if task.command_type in FORBIDDEN_COMMANDS:
            raise R7InvariantError("SCHEDULER_CANNOT_GRANT_AUTHORITY")
        if task.created_seq != self._task_seq + 1:
            raise R7InvariantError("TASK_SEQUENCE_INVALID")
        self._task_seq += 1
        self._tasks.append(task)

    def next_task(self) -> GovernanceTask | None:
        if not self._tasks:
            return None
        self._tasks.sort(
            key=lambda task: (-task.priority, task.created_seq, task.task_id)
        )
        return self._tasks.pop(0)

    def communicate(self, envelope: CommunicationEnvelope) -> None:
        self._require_governor(envelope.source_governor_id)
        self._require_governor(envelope.target_governor_id)
        if envelope.mission_id != self.mission_id:
            raise R7InvariantError("COMMUNICATION_MISSION_MISMATCH")
        self._communications.append(envelope)

    def execute(
        self,
        command: GovernanceCommand,
        *,
        now: float,
    ) -> GovernanceReceipt:
        contract = self._require_governor(command.governor_id)
        fingerprint = self._hash(asdict(command))
        replay = self._idempotency.get(command.idempotency_key)
        if replay is not None:
            previous_fingerprint, previous_receipt = replay
            if previous_fingerprint != fingerprint:
                raise R7InvariantError("IDEMPOTENCY_KEY_DIVERGENT_COMMAND")
            if previous_receipt.state_version_after > self._state_version:
                raise R7InvariantError(
                    "IDEMPOTENCY_REPLAY_AFTER_ROLLBACK_REQUIRES_NEW_KEY"
                )
            return self._record_replay_receipt(command, previous_receipt)

        before = self._state_version
        reason = self._validate_command(command, contract, now=now)
        if reason is not None:
            return self._record_receipt(
                command=command,
                status=CommandStatus.DENIED,
                reason=reason,
                state_version_before=before,
                state_version_after=before,
                mutation_count=0,
                material_effect_performed=False,
                fingerprint=fingerprint,
            )

        if self._failure_point is FailurePoint.AFTER_VALIDATION:
            self._failure_point = FailurePoint.NONE
            raise RuntimeError("injected_failure_after_validation")

        staged = dict(self._state)
        staged.update(command.write_set)
        next_version = before + (1 if command.write_set else 0)

        if self._failure_point is FailurePoint.BEFORE_COMMIT:
            self._failure_point = FailurePoint.NONE
            raise RuntimeError("injected_failure_before_commit")

        self._state = staged
        self._state_version = next_version
        lease = self._leases[command.lease_id]
        self._leases[command.lease_id] = replace(
            lease,
            uses=lease.uses + 1,
        )

        receipt = self._record_receipt(
            command=command,
            status=CommandStatus.ACCEPTED,
            reason="GOVERNED_STATE_COMMIT",
            state_version_before=before,
            state_version_after=next_version,
            mutation_count=len(command.write_set),
            material_effect_performed=False,
            fingerprint=fingerprint,
        )

        if self._failure_point is FailurePoint.AFTER_COMMIT:
            self._failure_point = FailurePoint.NONE
            raise RuntimeError(
                f"injected_failure_after_commit:{receipt.receipt_id}"
            )
        return receipt

    def checkpoint(
        self,
        checkpoint_id: str,
        *,
        now: float,
    ) -> RecoveryCheckpoint:
        if not checkpoint_id:
            raise ValueError("checkpoint_id_required")
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]
        checkpoint = RecoveryCheckpoint(
            checkpoint_id=checkpoint_id,
            mission_id=self.mission_id,
            generation=max(self._generation_by_governor.values(), default=1),
            state_version=self._state_version,
            state=dict(self._state),
            predecessor_receipt_hash=(
                self._receipts[-1].receipt_hash if self._receipts else "GENESIS"
            ),
            created_at=now,
        )
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint

    def restore_checkpoint(self, checkpoint_id: str) -> None:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint is None:
            raise R7InvariantError("RECOVERY_CHECKPOINT_NOT_FOUND")
        self._state = dict(checkpoint.state)
        self._state_version = checkpoint.state_version

    def recover_governor(
        self,
        governor_id: str,
        *,
        checkpoint_id: str,
    ) -> int:
        previous_generation = self.current_generation(governor_id)
        next_generation = self.fence_generation(governor_id)
        if next_generation != previous_generation + 1:
            raise R7InvariantError("RECOVERY_GENERATION_DIVERGENCE")
        self.restore_checkpoint(checkpoint_id)
        return next_generation

    def rollback_to_checkpoint(self, checkpoint_id: str) -> None:
        """Rollback internal state only; external effects are out of scope."""
        self.restore_checkpoint(checkpoint_id)

    def verify_receipt_chain(self) -> bool:
        previous = "GENESIS"
        for receipt in self._receipts:
            if receipt.previous_hash != previous:
                return False
            payload = asdict(receipt)
            recorded_hash = payload.pop("receipt_hash")
            if self._hash(payload) != recorded_hash:
                return False
            previous = receipt.receipt_hash
        return True

    def _validate_command(
        self,
        command: GovernanceCommand,
        contract: GovernorContract,
        *,
        now: float,
    ) -> str | None:
        if command.mission_id != self.mission_id:
            return "MISSION_MISMATCH"
        if command.command_type in FORBIDDEN_COMMANDS:
            return "FORBIDDEN_AUTHORITY_COMMAND"
        if command.command_type not in contract.allowed_commands:
            return "COMMAND_NOT_ALLOWED"
        if command.material_effect_requested:
            return "R7_INTERNAL_GOVERNANCE_CANNOT_EXECUTE_MATERIAL_EFFECT"
        if command.expected_state_version != self._state_version:
            return "STALE_STATE_VERSION"
        if command.generation != self._generation_by_governor[command.governor_id]:
            return "STALE_GENERATION"
        lease = self._leases.get(command.lease_id)
        if lease is None:
            return "LEASE_NOT_FOUND"
        if lease.governor_id != command.governor_id:
            return "LEASE_GOVERNOR_MISMATCH"
        if lease.mission_id != command.mission_id:
            return "LEASE_MISSION_MISMATCH"
        if lease.authority_ref != command.authority_ref:
            return "AUTHORITY_REF_MISMATCH"
        if lease.status is not LeaseStatus.ACTIVE:
            return "LEASE_NOT_ACTIVE"
        if now < lease.not_before or now >= lease.expires_at:
            return "LEASE_EXPIRED_OR_NOT_YET_VALID"
        if lease.generation != command.generation:
            return "LEASE_GENERATION_MISMATCH"
        if lease.uses >= lease.max_uses:
            return "LEASE_USE_EXHAUSTED"
        if command.scope and not set(command.scope).issubset(set(lease.scope)):
            return "LEASE_SCOPE_MISMATCH"
        owned = set(contract.owned_state_keys)
        if not set(command.write_set).issubset(owned):
            return "STATE_OWNERSHIP_VIOLATION"
        return None

    def _record_replay_receipt(
        self,
        command: GovernanceCommand,
        original: GovernanceReceipt,
    ) -> GovernanceReceipt:
        previous = self._receipts[-1].receipt_hash if self._receipts else "GENESIS"
        payload: dict[str, Any] = {
            "receipt_id": f"r7:{len(self._receipts) + 1}:{command.command_id}:replay",
            "command_id": command.command_id,
            "idempotency_key": command.idempotency_key,
            "status": CommandStatus.REPLAYED,
            "reason": f"EXACT_REPLAY_OF:{original.receipt_id}",
            "generation": command.generation,
            "state_version_before": self._state_version,
            "state_version_after": self._state_version,
            "mutation_count": 0,
            "material_effect_performed": False,
            "previous_hash": previous,
            "readback": dict(original.readback),
        }
        receipt = GovernanceReceipt(
            receipt_hash=self._hash(payload),
            **payload,
        )
        self._receipts.append(receipt)
        return receipt

    def _record_receipt(
        self,
        *,
        command: GovernanceCommand,
        status: CommandStatus,
        reason: str,
        state_version_before: int,
        state_version_after: int,
        mutation_count: int,
        material_effect_performed: bool,
        fingerprint: str,
    ) -> GovernanceReceipt:
        previous = self._receipts[-1].receipt_hash if self._receipts else "GENESIS"
        payload: dict[str, Any] = {
            "receipt_id": f"r7:{len(self._receipts) + 1}:{command.command_id}",
            "command_id": command.command_id,
            "idempotency_key": command.idempotency_key,
            "status": status,
            "reason": reason,
            "generation": command.generation,
            "state_version_before": state_version_before,
            "state_version_after": state_version_after,
            "mutation_count": mutation_count,
            "material_effect_performed": material_effect_performed,
            "previous_hash": previous,
            "readback": {
                key: self._state.get(key) for key in command.write_set
            },
        }
        receipt = GovernanceReceipt(
            receipt_hash=self._hash(payload),
            **payload,
        )
        self._receipts.append(receipt)
        self._idempotency[command.idempotency_key] = (fingerprint, receipt)
        return receipt

    def _require_governor(self, governor_id: str) -> GovernorContract:
        contract = self._governors.get(governor_id)
        if contract is None:
            raise R7InvariantError("GOVERNOR_NOT_REGISTERED")
        return contract
