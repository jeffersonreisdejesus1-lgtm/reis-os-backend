"""Deterministic, non-authorizing receipt for an auxiliary operation."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256


class AuxiliaryReceiptState(StrEnum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"
    FAILED = "failed"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class AuxiliaryEvidenceReference:
    evidence_id: str
    evidence_type: str
    locator: str | None = None


@dataclass(frozen=True, slots=True)
class AuxiliaryReceipt:
    schema_version: str
    receipt_id: str
    operation_id: str
    mission_id: str
    parent_mission_id: str
    instance_id: str | None
    authority_reference: str
    executor_id: str | None
    capability: str
    payload_fingerprint: str
    execution_state: AuxiliaryReceiptState
    result_reference: str | None
    evidence_references: tuple[AuxiliaryEvidenceReference, ...]
    observed_at: str

    def canonical_identity(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "operation_id": self.operation_id,
            "mission_id": self.mission_id,
            "parent_mission_id": self.parent_mission_id,
            "instance_id": self.instance_id,
            "authority_reference": self.authority_reference,
            "executor_id": self.executor_id,
            "capability": self.capability,
            "payload_fingerprint": self.payload_fingerprint,
            "execution_state": self.execution_state.value,
            "result_reference": self.result_reference,
            "evidence_references": [asdict(item) for item in self.evidence_references],
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["execution_state"] = self.execution_state.value
        return value


def create_auxiliary_receipt(
    *,
    operation_id: str,
    mission_id: str,
    parent_mission_id: str,
    instance_id: str | None,
    authority_reference: str,
    executor_id: str | None,
    capability: str,
    payload_fingerprint: str,
    execution_state: AuxiliaryReceiptState,
    result_reference: str | None,
    evidence_references: tuple[AuxiliaryEvidenceReference, ...],
    observed_at: str,
) -> AuxiliaryReceipt:
    required = (
        operation_id,
        mission_id,
        parent_mission_id,
        authority_reference,
        capability,
        payload_fingerprint,
        observed_at,
    )
    if not all(required):
        raise ValueError("auxiliary_receipt_fields_required")
    provisional = AuxiliaryReceipt(
        schema_version="reis-os/auxiliary-receipt/v1",
        receipt_id="",
        operation_id=operation_id,
        mission_id=mission_id,
        parent_mission_id=parent_mission_id,
        instance_id=instance_id,
        authority_reference=authority_reference,
        executor_id=executor_id,
        capability=capability,
        payload_fingerprint=payload_fingerprint,
        execution_state=execution_state,
        result_reference=result_reference,
        evidence_references=evidence_references,
        observed_at=observed_at,
    )
    return AuxiliaryReceipt(
        schema_version=provisional.schema_version,
        receipt_id=provisional.canonical_identity(),
        operation_id=provisional.operation_id,
        mission_id=provisional.mission_id,
        parent_mission_id=provisional.parent_mission_id,
        instance_id=provisional.instance_id,
        authority_reference=provisional.authority_reference,
        executor_id=provisional.executor_id,
        capability=provisional.capability,
        payload_fingerprint=provisional.payload_fingerprint,
        execution_state=provisional.execution_state,
        result_reference=provisional.result_reference,
        evidence_references=provisional.evidence_references,
        observed_at=provisional.observed_at,
    )
