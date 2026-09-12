from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Iterable

from .authority_aware_discovery import AuthorityAwareDiscoveryResult


class OCSCompositionError(RuntimeError):
    """Fail-closed denial raised by the COI9 composition boundary."""


@dataclass(frozen=True, slots=True)
class OCSRecord:
    ocs_id: str
    ocs_version: str
    identity_ref: str
    constitution_ref: str
    cognitive_entrypoint: str
    runtime_endpoint: str
    supported_capabilities: tuple[str, ...]
    authority_requirements: tuple[str, ...]
    required_receipts: tuple[str, ...]
    healthy: bool = True

    def validate(self) -> None:
        required = {
            "ocs_id": self.ocs_id,
            "ocs_version": self.ocs_version,
            "identity_ref": self.identity_ref,
            "constitution_ref": self.constitution_ref,
            "cognitive_entrypoint": self.cognitive_entrypoint,
            "runtime_endpoint": self.runtime_endpoint,
        }
        for field, value in required.items():
            if not value.strip():
                raise OCSCompositionError(f"ocs_{field}_required")
        for name, values in {
            "supported_capabilities": self.supported_capabilities,
            "authority_requirements": self.authority_requirements,
            "required_receipts": self.required_receipts,
        }.items():
            if not values or any(not value.strip() for value in values):
                raise OCSCompositionError(f"ocs_{name}_required")


@dataclass(frozen=True, slots=True)
class OCSCompositionRequest:
    mission_id: str
    plan_hash: str
    required_capabilities: tuple[str, ...]
    governed_discovery_receipts: tuple[str, ...]

    def validate(self) -> None:
        if not self.mission_id.strip():
            raise OCSCompositionError("composition_mission_id_required")
        if not self.plan_hash.strip():
            raise OCSCompositionError("composition_plan_hash_required")
        if not self.required_capabilities or any(not value.strip() for value in self.required_capabilities):
            raise OCSCompositionError("composition_required_capabilities_required")
        if not self.governed_discovery_receipts or any(
            not value.strip() for value in self.governed_discovery_receipts
        ):
            raise OCSCompositionError("composition_discovery_receipts_required")


@dataclass(frozen=True, slots=True)
class OCSCompositionResult:
    mission_id: str
    plan_hash: str
    selected_ocs: tuple[OCSRecord, ...]
    capability_assignments: tuple[tuple[str, str], ...]
    discovery_receipts: tuple[str, ...]
    registry_snapshot: str
    composition_receipt: str


class InstitutionalOCSRegistry:
    def __init__(self) -> None:
        self._records: dict[str, OCSRecord] = {}

    def register(self, record: OCSRecord) -> None:
        record.validate()
        if record.ocs_id in self._records:
            raise OCSCompositionError("ocs_duplicate_registration")
        self._records[record.ocs_id] = record

    def records(self) -> tuple[OCSRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))


class GovernedOCSComposer:
    """COI9: compose registered OCSs from COI8 governed discovery evidence.

    Composition is deterministic and fail-closed. It selects only registered,
    healthy OCSs whose declared capability and receipt contracts cover the
    exact mission plan. It does not execute software or grant authority.
    """

    def __init__(self, registry: InstitutionalOCSRegistry) -> None:
        self._registry = registry

    def compose(
        self,
        request: OCSCompositionRequest,
        discoveries: Iterable[AuthorityAwareDiscoveryResult],
    ) -> OCSCompositionResult:
        request.validate()
        discovery_list = tuple(discoveries)
        if not discovery_list:
            raise OCSCompositionError("composition_governed_discovery_required")

        by_capability: dict[str, AuthorityAwareDiscoveryResult] = {}
        observed_receipts: list[str] = []
        for item in discovery_list:
            receipt = item.authority_receipt
            capability_id = item.capability_discovery.selected_capability.capability_id
            if receipt.mission_id != request.mission_id:
                raise OCSCompositionError("composition_mission_mismatch")
            if receipt.capability_id != capability_id:
                raise OCSCompositionError("composition_authority_capability_mismatch")
            if receipt.status != "AUTHORIZED":
                raise OCSCompositionError("composition_authority_not_authorized")
            if capability_id in by_capability:
                raise OCSCompositionError("composition_duplicate_capability_discovery")
            by_capability[capability_id] = item
            observed_receipts.append(item.governed_discovery_receipt)

        if tuple(sorted(observed_receipts)) != tuple(sorted(request.governed_discovery_receipts)):
            raise OCSCompositionError("composition_discovery_receipt_set_mismatch")
        if set(by_capability) != set(request.required_capabilities):
            raise OCSCompositionError("composition_capability_set_mismatch")

        records = self._registry.records()
        if not records:
            raise OCSCompositionError("composition_ocs_registry_empty")
        for record in records:
            record.validate()

        assignments: list[tuple[str, str]] = []
        selected: dict[str, OCSRecord] = {}
        for capability_id in request.required_capabilities:
            candidates = [
                record for record in records
                if record.healthy
                and capability_id in record.supported_capabilities
                and "MISSION_COGNITIVE_RECEIPT" in record.required_receipts
                and "ACTION_COGNITIVE_RECEIPT" in record.required_receipts
                and "AUTHORITY_RECEIPT" in record.required_receipts
            ]
            if not candidates:
                raise OCSCompositionError(f"composition_no_eligible_ocs:{capability_id}")
            candidates.sort(key=lambda item: (item.ocs_id, item.ocs_version))
            chosen = candidates[0]
            authority_requirements = set(
                by_capability[capability_id].capability_discovery.selected_capability.authorized_missions
            )
            if request.mission_id not in authority_requirements:
                raise OCSCompositionError("composition_capability_mission_not_authorized")
            selected[chosen.ocs_id] = chosen
            assignments.append((capability_id, chosen.ocs_id))

        selected_records = tuple(selected[key] for key in sorted(selected))
        registry_snapshot = self._digest([asdict(record) for record in records])
        composition_receipt = self._digest({
            "mission_id": request.mission_id,
            "plan_hash": request.plan_hash,
            "selected_ocs": [asdict(record) for record in selected_records],
            "capability_assignments": assignments,
            "governed_discovery_receipts": sorted(observed_receipts),
            "registry_snapshot": registry_snapshot,
        })
        return OCSCompositionResult(
            mission_id=request.mission_id,
            plan_hash=request.plan_hash,
            selected_ocs=selected_records,
            capability_assignments=tuple(assignments),
            discovery_receipts=tuple(sorted(observed_receipts)),
            registry_snapshot=registry_snapshot,
            composition_receipt=composition_receipt,
        )

    @staticmethod
    def _digest(payload: object) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode("utf-8")
        return sha256(encoded).hexdigest()
