from __future__ import annotations

from copy import deepcopy
from typing import Any

from .store import GovernanceLedger


class CommandGovernanceProjection:
    """Read-only Control Plane projection over bounded governance stores.

    This class intentionally exposes no mutation methods.
    """

    def __init__(self, ledger: GovernanceLedger) -> None:
        self._ledger = ledger

    def object_view(self, object_ref: str) -> dict[str, Any]:
        records = self._ledger.records(object_ref=object_ref)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            grouped.setdefault(record["record_type"], []).append(deepcopy(record["payload"]))
        return {
            "object_ref": object_ref,
            "evidence": grouped.get("EVIDENCE", []),
            "quality": grouped.get("QUALITY", []),
            "assurance": grouped.get("ASSURANCE", []),
            "readiness": grouped.get("READINESS", []),
            "founder_decisions": grouped.get("FOUNDER_DECISION", []),
            "metrics": grouped.get("METRIC", []),
            "refactors": grouped.get("REFACTOR", []),
        }

    def capability_view(self) -> dict[str, Any]:
        capabilities = deepcopy(self._ledger.capabilities())
        return {
            "capabilities": capabilities,
            "summary": {
                "total": len(capabilities),
                "validated": sum(1 for c in capabilities if c["connection_validated"]),
                "model_invokable": sum(
                    1
                    for c in capabilities
                    if c["connection_validated"] and c["can_model_invoke"]
                ),
                "machine_receipt_supported": sum(
                    1 for c in capabilities if c["machine_receipt_supported"]
                ),
            },
        }
