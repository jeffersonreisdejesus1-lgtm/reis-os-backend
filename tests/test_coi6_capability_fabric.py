from __future__ import annotations

from dataclasses import replace

import pytest

from app.cognitive_validation.capability_fabric import (
    CapabilityFabricError,
    CapabilityHealth,
    CapabilityRecord,
    InstitutionalCapabilityFabric,
)


def record() -> CapabilityRecord:
    return CapabilityRecord(
        capability_id="github",
        capability_version="1",
        adapter_id="github-adapter",
        adapter_version="1",
        endpoint="connector://github",
        schema_version="v1",
        health=CapabilityHealth.HEALTHY,
        authorized_missions=("mission-001",),
    )


def test_registered_healthy_authorized_compatible_capability_is_discoverable() -> None:
    fabric = InstitutionalCapabilityFabric([record()])
    result = fabric.discover("github", mission_id="mission-001", required_schema_version="v1")
    assert result.selected_capability.capability_id == "github"
    assert result.discovery_receipt
    assert result.registry_snapshot
    assert result.health_snapshot
    assert result.authority_snapshot
    assert result.schema_snapshot


def test_model_claim_absent_from_registry_is_denied() -> None:
    fabric = InstitutionalCapabilityFabric([record()])
    with pytest.raises(CapabilityFabricError, match="capability_not_registered"):
        fabric.discover("hallucinated-capability", mission_id="mission-001", required_schema_version="v1")


def test_unhealthy_capability_is_denied() -> None:
    fabric = InstitutionalCapabilityFabric([replace(record(), health=CapabilityHealth.DEGRADED)])
    with pytest.raises(CapabilityFabricError, match="capability_not_healthy"):
        fabric.discover("github", mission_id="mission-001", required_schema_version="v1")


def test_unavailable_capability_is_denied() -> None:
    fabric = InstitutionalCapabilityFabric([replace(record(), health=CapabilityHealth.UNAVAILABLE)])
    with pytest.raises(CapabilityFabricError, match="capability_not_healthy"):
        fabric.discover("github", mission_id="mission-001", required_schema_version="v1")


def test_schema_mismatch_is_denied() -> None:
    fabric = InstitutionalCapabilityFabric([record()])
    with pytest.raises(CapabilityFabricError, match="capability_schema_incompatible"):
        fabric.discover("github", mission_id="mission-001", required_schema_version="v2")


def test_unauthorized_mission_is_denied() -> None:
    fabric = InstitutionalCapabilityFabric([record()])
    with pytest.raises(CapabilityFabricError, match="capability_not_authorized_for_mission"):
        fabric.discover("github", mission_id="mission-002", required_schema_version="v1")


def test_duplicate_registration_is_denied() -> None:
    fabric = InstitutionalCapabilityFabric([record()])
    with pytest.raises(CapabilityFabricError, match="capability_duplicate_registration"):
        fabric.register(record())


def test_missing_adapter_binding_is_denied_at_registration() -> None:
    with pytest.raises(CapabilityFabricError, match="capability_adapter_id_required"):
        InstitutionalCapabilityFabric([replace(record(), adapter_id="")])


def test_missing_endpoint_is_denied_at_registration() -> None:
    with pytest.raises(CapabilityFabricError, match="capability_endpoint_required"):
        InstitutionalCapabilityFabric([replace(record(), endpoint="")])


def test_empty_authority_scope_is_denied_at_registration() -> None:
    with pytest.raises(CapabilityFabricError, match="capability_authorized_missions_required"):
        InstitutionalCapabilityFabric([replace(record(), authorized_missions=())])


def test_discovery_receipt_is_context_bound() -> None:
    r = replace(record(), authorized_missions=("mission-001", "mission-002"))
    fabric = InstitutionalCapabilityFabric([r])
    first = fabric.discover("github", mission_id="mission-001", required_schema_version="v1")
    second = fabric.discover("github", mission_id="mission-002", required_schema_version="v1")
    assert first.discovery_receipt != second.discovery_receipt
    assert first.authority_snapshot != second.authority_snapshot
