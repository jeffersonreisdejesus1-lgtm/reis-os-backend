from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class RecoveryReceipt:
    operation_id: str
    decision: str
    observed_state: str
    effect_observed: bool | None
    evidence_reference: str | None
    schema_version: str = "1.0"

    @property
    def digest(self) -> str:
        payload = {
            "decision": self.decision,
            "effect_observed": self.effect_observed,
            "evidence_reference": self.evidence_reference,
            "observed_state": self.observed_state,
            "operation_id": self.operation_id,
            "schema_version": self.schema_version,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return sha256(encoded).hexdigest()


def reconcile_receipt(
    *,
    operation_id: str,
    decision: str,
    observed_state: str,
    effect_observed: bool | None,
    evidence_reference: str | None,
) -> RecoveryReceipt:
    if not operation_id:
        raise ValueError("operation_id is required")
    if decision == "RECONCILE" and not evidence_reference:
        raise ValueError("reconciliation requires evidence_reference")
    if effect_observed is None and decision != "HOLD":
        raise ValueError("uncertain effect requires HOLD")
    return RecoveryReceipt(
        operation_id=operation_id,
        decision=decision,
        observed_state=observed_state,
        effect_observed=effect_observed,
        evidence_reference=evidence_reference,
    )
