from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from app.profile_bindings.profiles import OCSProfile, get_profile


class SofiaBindingError(PermissionError):
    """Fail-closed errors for the bounded SOFIA P01 binding."""


class SofiaExecutionState(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    REPLAYED = "REPLAYED"


@dataclass(frozen=True)
class SofiaMissionRequest:
    mission_id: str
    operation_id: str
    capability: str
    authority_ref: str | None = None
    handoff_id: str | None = None
    payload: Mapping[str, object] = None  # type: ignore[assignment]

    def validate(self) -> None:
        if not self.mission_id or not self.operation_id:
            raise SofiaBindingError("mission_and_operation_required")
        if not self.capability:
            raise SofiaBindingError("capability_required")
        if not self.authority_ref:
            raise SofiaBindingError("authority_reference_required")


@dataclass(frozen=True)
class SofiaExecutionReceipt:
    schema_version: str
    receipt_id: str
    mission_id: str
    operation_id: str
    ocs_id: str
    identity_ref: str
    state_namespace: str
    memory_namespace: str
    capability: str
    authority_ref: str
    payload_digest: str
    state: SofiaExecutionState
    replay: bool

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "mission_id": self.mission_id,
            "operation_id": self.operation_id,
            "ocs_id": self.ocs_id,
            "identity_ref": self.identity_ref,
            "state_namespace": self.state_namespace,
            "memory_namespace": self.memory_namespace,
            "capability": self.capability,
            "authority_ref": self.authority_ref,
            "payload_digest": self.payload_digest,
        }


@dataclass(frozen=True)
class SofiaBindingResult:
    ocs_id: str
    identity_ref: str
    specialty: str
    state_namespace: str
    memory_namespace: str
    mission_id: str
    operation_id: str
    authority_ref: str
    capability: str
    receipt: SofiaExecutionReceipt


def _digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class SofiaP01Executor:
    """Bounded local, non-material executor for SOFIA's P01 physiology."""

    def __init__(self) -> None:
        self.profile: OCSProfile = get_profile("SOFIA")
        self._readback: dict[str, SofiaBindingResult] = {}
        self.execution_count = 0

    def execute(self, request: SofiaMissionRequest) -> SofiaBindingResult:
        request.validate()
        if request.capability != self.profile.specialty:
            raise SofiaBindingError("capability_incompatible_with_sofia")
        if request.authority_ref != self.profile.authority_envelope_ref:
            raise SofiaBindingError("authority_reference_not_bound_to_sofia")
        existing = self._readback.get(request.operation_id)
        payload = dict(request.payload or {})
        payload_digest = _digest(payload)
        if existing is not None:
            if existing.receipt.payload_digest != payload_digest:
                raise SofiaBindingError("operation_payload_conflict")
            replay_receipt = SofiaExecutionReceipt(
                **{
                    **existing.receipt.__dict__,
                    "state": SofiaExecutionState.REPLAYED,
                    "replay": True,
                }
            )
            return SofiaBindingResult(**{
                **existing.__dict__, "receipt": replay_receipt
            })
        receipt_id = _digest({
            "operation_id": request.operation_id,
            "mission_id": request.mission_id,
            "payload_digest": payload_digest,
            "authority_ref": request.authority_ref,
        })
        receipt = SofiaExecutionReceipt(
            schema_version="sofia-p01/v1",
            receipt_id=receipt_id,
            mission_id=request.mission_id,
            operation_id=request.operation_id,
            ocs_id="SOFIA",
            identity_ref=self.profile.identity,
            state_namespace=self.profile.state_namespace,
            memory_namespace=self.profile.memory_namespace,
            capability=request.capability,
            authority_ref=request.authority_ref,
            payload_digest=payload_digest,
            state=SofiaExecutionState.SUCCEEDED,
            replay=False,
        )
        result = SofiaBindingResult(
            ocs_id="SOFIA",
            identity_ref=self.profile.identity,
            specialty=self.profile.specialty,
            state_namespace=self.profile.state_namespace,
            memory_namespace=self.profile.memory_namespace,
            mission_id=request.mission_id,
            operation_id=request.operation_id,
            authority_ref=request.authority_ref,
            capability=request.capability,
            receipt=receipt,
        )
        self._readback[request.operation_id] = result
        self.execution_count += 1
        return result

    def readback(self, operation_id: str) -> SofiaBindingResult:
        try:
            return self._readback[operation_id]
        except KeyError as exc:
            raise SofiaBindingError("operation_readback_missing") from exc
