import pytest

from app.cognitive_validation.adapter_fabric import (
    AdapterFabricError,
    AdapterHealth,
    AdapterInvocationContext,
    AdapterRecord,
    InstitutionalAdapterFabric,
)
from app.cognitive_validation.capability_fabric import (
    CapabilityHealth,
    CapabilityRecord,
    InstitutionalCapabilityFabric,
)


def capability_and_discovery():
    record = CapabilityRecord(
        capability_id="github",
        capability_version="1",
        adapter_id="github-adapter",
        adapter_version="7",
        endpoint="github://repo",
        schema_version="v1",
        health=CapabilityHealth.HEALTHY,
        authorized_missions=("MISSION-1",),
    )
    fabric = InstitutionalCapabilityFabric((record,))
    return record, fabric.discover("github", mission_id="MISSION-1", required_schema_version="v1")


def adapter_record(**changes):
    values = dict(
        adapter_id="github-adapter",
        adapter_version="7",
        capability_id="github",
        capability_version="1",
        endpoint="github://repo",
        input_schema_version="v1",
        output_schema_version="v1",
        health=AdapterHealth.HEALTHY,
    )
    values.update(changes)
    return AdapterRecord(**values)


def context(discovery, **changes):
    values = dict(
        mission_id="MISSION-1",
        action_receipt_id="ACTION-RECEIPT-1",
        authority_receipt_id="AUTHORITY-RECEIPT-1",
        capability_discovery_receipt=discovery.discovery_receipt,
        input_schema_version="v1",
        expected_output_schema_version="v1",
    )
    values.update(changes)
    return AdapterInvocationContext(**values)


def test_executes_exact_registered_adapter_and_emits_receipt():
    _, discovery = capability_and_discovery()
    fabric = InstitutionalAdapterFabric()
    fabric.register(adapter_record(), lambda payload: {"ok": True, "echo": payload["x"]})
    response, receipt = fabric.execute(discovery, context(discovery), {"x": 3})
    assert response == {"ok": True, "echo": 3}
    assert receipt.status == "EXECUTED_CONFIRMED"
    assert receipt.action_receipt_id == "ACTION-RECEIPT-1"
    assert receipt.authority_receipt_id == "AUTHORITY-RECEIPT-1"
    assert receipt.discovery_receipt == discovery.discovery_receipt
    assert receipt.execution_receipt


@pytest.mark.parametrize("changes,error", [
    ({"mission_id": "OTHER"}, "adapter_mission_mismatch"),
    ({"capability_discovery_receipt": "fake"}, "adapter_discovery_receipt_mismatch"),
    ({"input_schema_version": "v2"}, "adapter_input_schema_incompatible"),
    ({"expected_output_schema_version": "v2"}, "adapter_output_schema_incompatible"),
    ({"action_receipt_id": ""}, "adapter_context_action_receipt_id_required"),
    ({"authority_receipt_id": ""}, "adapter_context_authority_receipt_id_required"),
])
def test_context_mismatch_fails_closed(changes, error):
    _, discovery = capability_and_discovery()
    fabric = InstitutionalAdapterFabric()
    fabric.register(adapter_record(), lambda payload: {"ok": True})
    with pytest.raises(AdapterFabricError, match=error):
        fabric.execute(discovery, context(discovery, **changes), {})


@pytest.mark.parametrize("record,error", [
    (adapter_record(health=AdapterHealth.UNAVAILABLE), "adapter_not_healthy"),
    (adapter_record(adapter_version="8"), "adapter_version_mismatch"),
    (adapter_record(capability_id="not-github"), "adapter_capability_mismatch"),
    (adapter_record(capability_version="2"), "adapter_capability_version_mismatch"),
    (adapter_record(endpoint="github://other"), "adapter_endpoint_mismatch"),
    (adapter_record(input_schema_version="v2"), "adapter_capability_schema_mismatch"),
])
def test_adapter_binding_mismatch_fails_closed(record, error):
    _, discovery = capability_and_discovery()
    fabric = InstitutionalAdapterFabric()
    fabric.register(record, lambda payload: {"ok": True})
    with pytest.raises(AdapterFabricError, match=error):
        fabric.execute(discovery, context(discovery), {})


def test_unregistered_adapter_is_denied():
    _, discovery = capability_and_discovery()
    with pytest.raises(AdapterFabricError, match="adapter_not_registered"):
        InstitutionalAdapterFabric().execute(discovery, context(discovery), {})


def test_duplicate_adapter_registration_is_denied():
    fabric = InstitutionalAdapterFabric()
    fabric.register(adapter_record(), lambda payload: {})
    with pytest.raises(AdapterFabricError, match="adapter_duplicate_registration"):
        fabric.register(adapter_record(), lambda payload: {})


def test_handler_failure_is_fail_closed():
    _, discovery = capability_and_discovery()
    fabric = InstitutionalAdapterFabric()
    def broken(payload):
        raise RuntimeError("boom")
    fabric.register(adapter_record(), broken)
    with pytest.raises(AdapterFabricError, match="adapter_execution_failed"):
        fabric.execute(discovery, context(discovery), {})


def test_invalid_handler_response_is_denied():
    _, discovery = capability_and_discovery()
    fabric = InstitutionalAdapterFabric()
    fabric.register(adapter_record(), lambda payload: "not-a-mapping")
    with pytest.raises(AdapterFabricError, match="adapter_invalid_response"):
        fabric.execute(discovery, context(discovery), {})
