from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from json import dumps
from typing import Iterable


class CapabilityFabricError(RuntimeError):
    """Fail-closed denial raised by the COI6 capability fabric."""


class CapabilityHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    capability_id: str
    capability_version: str
    adapter_id: str
    adapter_version: str
    endpoint: str
    schema_version: str
    health: CapabilityHealth
    authorized_missions: tuple[str, ...]

    def validate(self) -> None:
        required = {
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "endpoint": self.endpoint,
            "schema_version": self.schema_version,
        }
        for field, value in required.items():
            if not value.strip():
                raise CapabilityFabricError(f"capability_{field}_required")
        if not self.authorized_missions:
            raise CapabilityFabricError("capability_authorized_missions_required")
        if any(not mission.strip() for mission in self.authorized_missions):
            raise CapabilityFabricError("capability_authorized_mission_invalid")


@dataclass(frozen=True, slots=True)
class CapabilityDiscoveryResult:
    mission_id: str
    requested_capability_id: str
    selected_capability: CapabilityRecord
    registry_snapshot: str
    health_snapshot: str
    authority_snapshot: str
    schema_snapshot: str
    discovery_receipt: str


class InstitutionalCapabilityFabric:
    """Canonical COI6 registry and fail-closed capability discovery boundary.

    A model claim never creates a capability. Discovery succeeds only for a
    registered capability that is adapter-bound, healthy, schema-compatible,
    endpoint-valid, and authorized for the current mission.
    """

    def __init__(self, records: Iterable[CapabilityRecord] = ()) -> None:
        self._records: dict[str, CapabilityRecord] = {}
        for record in records:
            self.register(record)

    def register(self, record: CapabilityRecord) -> None:
        record.validate()
        if record.capability_id in self._records:
            raise CapabilityFabricError("capability_duplicate_registration")
        self._records[record.capability_id] = record

    def discover(
        self,
        capability_id: str,
        *,
        mission_id: str,
        required_schema_version: str,
    ) -> CapabilityDiscoveryResult:
        if not capability_id.strip():
            raise CapabilityFabricError("capability_id_required")
        if not mission_id.strip():
            raise CapabilityFabricError("capability_mission_id_required")
        if not required_schema_version.strip():
            raise CapabilityFabricError("capability_schema_version_required")

        record = self._records.get(capability_id)
        if record is None:
            raise CapabilityFabricError("capability_not_registered")
        record.validate()
        if record.health is not CapabilityHealth.HEALTHY:
            raise CapabilityFabricError("capability_not_healthy")
        if record.schema_version != required_schema_version:
            raise CapabilityFabricError("capability_schema_incompatible")
        if mission_id not in record.authorized_missions:
            raise CapabilityFabricError("capability_not_authorized_for_mission")

        registry_snapshot = self._digest({
            "capability_id": record.capability_id,
            "capability_version": record.capability_version,
            "adapter_id": record.adapter_id,
            "adapter_version": record.adapter_version,
            "endpoint": record.endpoint,
        })
        health_snapshot = self._digest({"health": record.health.value})
        authority_snapshot = self._digest({
            "mission_id": mission_id,
            "authorized_missions": record.authorized_missions,
        })
        schema_snapshot = self._digest({"schema_version": record.schema_version})
        discovery_receipt = self._digest({
            "mission_id": mission_id,
            "capability_id": record.capability_id,
            "registry_snapshot": registry_snapshot,
            "health_snapshot": health_snapshot,
            "authority_snapshot": authority_snapshot,
            "schema_snapshot": schema_snapshot,
        })
        return CapabilityDiscoveryResult(
            mission_id=mission_id,
            requested_capability_id=capability_id,
            selected_capability=record,
            registry_snapshot=registry_snapshot,
            health_snapshot=health_snapshot,
            authority_snapshot=authority_snapshot,
            schema_snapshot=schema_snapshot,
            discovery_receipt=discovery_receipt,
        )

    @staticmethod
    def _digest(payload: object) -> str:
        encoded = dumps(payload, sort_keys=True, separators=(",", ":"), default=list).encode()
        return sha256(encoded).hexdigest()
