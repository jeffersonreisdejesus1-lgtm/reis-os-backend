from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.ocs_instances.contracts import (
    InstanceBinding,
    InstanceBindingError,
    InstanceStatus,
    canonical_hash,
)
from app.ocs_instances.store import InstanceBindingStore
from app.profile_bindings.profiles import PROFILES
from app.universal_kernel.governance import AuthorityLeaseManager, LeaseState
from app.universal_kernel.hazel_continuity import HazelBoundContinuity


@dataclass(frozen=True)
class RecoveryResult:
    binding: InstanceBinding
    hazel_state_version: int
    hazel_event_hash: str
    saga_state: str | None


class OCSInstanceRecovery:
    """Cold-start reconciliation for one mission-scoped OCS lineage.

    Hazel remains the continuity authority. The local registry is a durable
    coordination projection and may only be promoted after an exact Hazel readback.
    """

    def __init__(
        self,
        *,
        store: InstanceBindingStore,
        leases: AuthorityLeaseManager,
        continuity: HazelBoundContinuity,
    ) -> None:
        self._store = store
        self._leases = leases
        self._continuity = continuity

    def recover_instance(
        self,
        organization_id: str,
        mission_id: str,
        ocs_id: str,
    ) -> RecoveryResult:
        binding = self._latest_binding(organization_id, mission_id, ocs_id)
        self._validate_local_identity(binding)
        self._require_single_active_generation(organization_id, mission_id, ocs_id)

        saga_state: str | None = None
        if (
            binding.predecessor_binding_id is not None
            and binding.status is InstanceStatus.PREPARED
        ):
            binding, saga_state = self._reconcile_replacement(binding)

        recovered = self._recover_hazel(binding)
        self._validate_hazel_fidelity(binding, recovered)
        return RecoveryResult(
            binding=binding,
            hazel_state_version=int(recovered["state_version"]),
            hazel_event_hash=str(recovered["event_hash"]),
            saga_state=saga_state,
        )

    def _reconcile_replacement(
        self, successor: InstanceBinding
    ) -> tuple[InstanceBinding, str]:
        predecessor_id = successor.predecessor_binding_id
        if predecessor_id is None:
            raise InstanceBindingError("replacement_predecessor_required")
        predecessor = self._store.get(predecessor_id)
        saga = self._replacement_saga(predecessor.binding_id)
        saga_id = str(saga["idempotency_key"])
        saga_payload = json.loads(str(saga["payload_json"]))
        lease_id = str(saga_payload.get("lease_id", ""))
        if lease_id != successor.lease_id:
            raise InstanceBindingError("replacement_recovery_lease_mismatch")
        lease = self._leases.lease_for(lease_id)
        if lease.authority_ref != successor.authority_ref:
            raise InstanceBindingError("replacement_recovery_authority_mismatch")

        recovered = self._continuity.recover_state(
            run_id=successor.run_id,
            expected_ocs=successor.ocs_id,
            host=successor.host,
            authority_ref=successor.authority_ref,
        )
        next_version = predecessor.checkpoint_version + 1
        replacement_state = {
            "binding_id": successor.binding_id,
            "mission_id": successor.mission_id,
            "generation": successor.generation,
            "recovered_from": predecessor.binding_id,
            "recovered_payload": recovered["payload"],
            "bootstrap_hash": successor.bootstrap_hash,
        }

        recovered_version = int(recovered["state_version"])
        if recovered_version == predecessor.checkpoint_version:
            persisted = self._continuity.persist_state(
                run_id=successor.run_id,
                expected_ocs=successor.ocs_id,
                host=successor.host,
                authority_ref=successor.authority_ref,
                state_version=next_version,
                predecessor_hash=predecessor.hazel_event_hash,
                state=replacement_state,
                trace_id=f"trace:{successor.binding_id}:cold-recovery",
            )
            persisted_hash = persisted.receipt.get("event_hash")
        elif recovered_version == next_version:
            expected_payload = dict(replacement_state)
            current_payload = recovered.get("payload")
            if not isinstance(current_payload, dict):
                raise InstanceBindingError("replacement_recovery_payload_invalid")
            # Once the replacement effect exists, the nested recovered payload is
            # already embedded in Hazel and must be preserved exactly.
            expected_payload["recovered_payload"] = current_payload.get(
                "recovered_payload"
            )
            if current_payload != expected_payload:
                raise InstanceBindingError("replacement_recovery_conflict")
            persisted_hash = recovered.get("event_hash")
        else:
            raise InstanceBindingError("replacement_state_version_conflict")

        saga_state = str(saga["state"])
        if saga_state == "LEASE_RESERVED":
            saga = self._store.advance_action_saga(
                saga_id,
                expected_state="LEASE_RESERVED",
                target_state="EFFECT_APPLIED",
            )
            saga_state = str(saga["state"])

        recovered = self._continuity.recover_state(
            run_id=successor.run_id,
            expected_ocs=successor.ocs_id,
            host=successor.host,
            authority_ref=successor.authority_ref,
        )
        self._validate_replacement_hazel(
            predecessor, successor, recovered, expected_version=next_version
        )
        if recovered.get("event_hash") != persisted_hash:
            raise InstanceBindingError("replacement_readback_mismatch")

        if saga_state == "EFFECT_APPLIED":
            saga = self._store.advance_action_saga(
                saga_id,
                expected_state="EFFECT_APPLIED",
                target_state="READBACK_VERIFIED",
            )
            saga_state = str(saga["state"])

        predecessor = self._store.get(predecessor.binding_id)
        successor = self._store.get(successor.binding_id)
        if (
            predecessor.status is InstanceStatus.CHECKPOINTED
            and successor.status is InstanceStatus.PREPARED
        ):
            _, successor = self._store.commit_replacement(
                predecessor_id=predecessor.binding_id,
                predecessor_expected_version=predecessor.version,
                successor_id=successor.binding_id,
                successor_expected_version=successor.version,
                idempotency_key=saga_id,
                checkpoint_version=next_version,
                checkpoint_hash=str(recovered["payload_hash"]),
                hazel_event_hash=str(recovered["event_hash"]),
            )

        predecessor = self._store.get(predecessor.binding_id)
        successor = self._store.get(successor.binding_id)
        if (
            predecessor.status is not InstanceStatus.REPLACED
            or successor.status not in {
                InstanceStatus.PERSISTED,
                InstanceStatus.BOUND,
                InstanceStatus.ACTIVE,
                InstanceStatus.CHECKPOINTED,
            }
        ):
            raise InstanceBindingError("replacement_local_commit_incomplete")

        saga = self._store.action_saga(saga_id)
        saga_state = str(saga["state"])
        if saga_state == "READBACK_VERIFIED":
            saga = self._store.advance_action_saga(
                saga_id,
                expected_state="READBACK_VERIFIED",
                target_state="LOCAL_COMMITTED",
            )
            saga_state = str(saga["state"])
        if saga_state == "LOCAL_COMMITTED":
            lease = self._leases.lease_for(successor.lease_id)
            if lease.state is not LeaseState.RELEASED:
                self._leases.finalize(lease.lease_id)
            saga = self._store.advance_action_saga(
                saga_id,
                expected_state="LOCAL_COMMITTED",
                target_state="LEASE_FINALIZED",
            )
            saga_state = str(saga["state"])
        if saga_state != "LEASE_FINALIZED":
            raise InstanceBindingError("replacement_recovery_saga_incomplete")
        return successor, saga_state

    def _validate_local_identity(self, binding: InstanceBinding) -> None:
        profile = PROFILES.get(binding.ocs_id)
        if profile is None:
            raise InstanceBindingError("recovery_unknown_ocs_identity")
        if binding.profile_version != profile.version:
            raise InstanceBindingError("recovery_profile_version_drift")
        if binding.profile_hash != canonical_hash(profile.__dict__):
            # canonical profile hashing in the binder uses dataclass asdict; __dict__
            # contains the same declared data for these frozen profile records.
            from dataclasses import asdict

            if binding.profile_hash != canonical_hash(asdict(profile)):
                raise InstanceBindingError("recovery_profile_hash_drift")
        if binding.authority_ref != profile.authority_envelope_ref:
            raise InstanceBindingError("recovery_authority_ref_drift")
        if binding.state_namespace != profile.state_namespace:
            raise InstanceBindingError("recovery_state_namespace_drift")
        if binding.memory_namespace != profile.memory_namespace:
            raise InstanceBindingError("recovery_memory_namespace_drift")
        lease = self._leases.lease_for(binding.lease_id)
        if lease.authority_ref != binding.authority_ref:
            raise InstanceBindingError("recovery_lease_authority_drift")

    def _recover_hazel(self, binding: InstanceBinding) -> dict[str, Any]:
        return self._continuity.recover_state(
            run_id=binding.run_id,
            expected_ocs=binding.ocs_id,
            host=binding.host,
            authority_ref=binding.authority_ref,
        )

    def _validate_hazel_fidelity(
        self, binding: InstanceBinding, recovered: dict[str, Any]
    ) -> None:
        if int(recovered["state_version"]) != binding.checkpoint_version:
            raise InstanceBindingError("recovery_state_version_mismatch")
        if str(recovered["event_hash"]) != binding.hazel_event_hash:
            raise InstanceBindingError("recovery_event_hash_mismatch")
        if str(recovered["payload_hash"]) != binding.checkpoint_hash:
            raise InstanceBindingError("recovery_payload_hash_mismatch")
        payload = recovered.get("payload")
        if not isinstance(payload, dict):
            raise InstanceBindingError("recovery_payload_invalid")
        if payload.get("binding_id") != binding.binding_id:
            raise InstanceBindingError("recovery_binding_lineage_mismatch")
        if payload.get("generation") != binding.generation:
            raise InstanceBindingError("recovery_generation_mismatch")
        if binding.predecessor_binding_id is not None:
            predecessor = self._store.get(binding.predecessor_binding_id)
            self._validate_replacement_hazel(
                predecessor,
                binding,
                recovered,
                expected_version=binding.checkpoint_version,
            )

    def _validate_replacement_hazel(
        self,
        predecessor: InstanceBinding,
        successor: InstanceBinding,
        recovered: dict[str, Any],
        *,
        expected_version: int,
    ) -> None:
        if int(recovered["state_version"]) != expected_version:
            raise InstanceBindingError("replacement_recovery_version_mismatch")
        if recovered.get("predecessor_hash") != predecessor.hazel_event_hash:
            raise InstanceBindingError("replacement_predecessor_hash_mismatch")
        payload = recovered.get("payload")
        if not isinstance(payload, dict):
            raise InstanceBindingError("replacement_recovery_payload_invalid")
        if payload.get("binding_id") != successor.binding_id:
            raise InstanceBindingError("replacement_recovery_binding_mismatch")
        if payload.get("recovered_from") != predecessor.binding_id:
            raise InstanceBindingError("replacement_recovered_from_mismatch")
        if payload.get("generation") != predecessor.generation + 1:
            raise InstanceBindingError("replacement_generation_mismatch")

    def _latest_binding(
        self, organization_id: str, mission_id: str, ocs_id: str
    ) -> InstanceBinding:
        with self._store._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM ocs_instance_bindings
                WHERE organization_id = ? AND mission_id = ? AND ocs_id = ?
                ORDER BY generation DESC LIMIT 1
                """,
                (organization_id, mission_id, ocs_id),
            ).fetchone()
        if row is None:
            raise InstanceBindingError("recovery_binding_not_found")
        return self._store._row(row)

    def _replacement_saga(self, predecessor_id: str) -> dict[str, Any]:
        with self._store._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM ocs_action_sagas
                WHERE binding_id = ? AND operation = 'ocs_instance_replacement'
                ORDER BY updated_at DESC LIMIT 1
                """,
                (predecessor_id,),
            ).fetchone()
        if row is None:
            raise InstanceBindingError("replacement_recovery_saga_missing")
        return dict(row)

    def _require_single_active_generation(
        self, organization_id: str, mission_id: str, ocs_id: str
    ) -> None:
        with self._store._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS active_count FROM ocs_instance_bindings
                WHERE organization_id = ? AND mission_id = ? AND ocs_id = ?
                  AND status = 'active'
                """,
                (organization_id, mission_id, ocs_id),
            ).fetchone()
        if row is not None and int(row["active_count"]) > 1:
            raise InstanceBindingError("multiple_active_generations_detected")
