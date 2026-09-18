from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from .action_receipt import ActionCognitiveReceipt
from .adapter_fabric import AdapterExecutionReceipt, AdapterInvocationContext, InstitutionalAdapterFabric
from .authority_aware_discovery import AuthorityAwareDiscoveryResult, AuthorityAwareCapabilityDiscovery
from .ocs_composition import OCSCompositionResult
from .runtime_anti_bypass import RuntimeAntiBypassGateway, RuntimeExecutionContext

class GovernedSoftwareExecutionError(RuntimeError): pass

@dataclass(frozen=True, slots=True)
class SoftwareSelectionRequest:
    mission_id: str; capability_id: str; ocs_id: str; composition_receipt: str
    governed_discovery_receipt: str; action_receipt_id: str; authority_receipt_id: str
    def validate(self) -> None:
        for field in ("mission_id","capability_id","ocs_id","composition_receipt","governed_discovery_receipt","action_receipt_id","authority_receipt_id"):
            if not getattr(self, field).strip(): raise GovernedSoftwareExecutionError(f"software_selection_{field}_required")

@dataclass(frozen=True, slots=True)
class GovernedSoftwareExecutionResult:
    mission_id: str; capability_id: str; ocs_id: str; adapter_id: str; adapter_version: str
    execution_status: str; adapter_execution_receipt: AdapterExecutionReceipt
    governed_execution_receipt: str; response: Mapping[str, object]

class GovernedSoftwareExecutor:
    """COI10 governed software selection/execution; COI11 owns evidence qualification."""
    def __init__(self, *, authority_discovery: AuthorityAwareCapabilityDiscovery, anti_bypass: RuntimeAntiBypassGateway, adapter_fabric: InstitutionalAdapterFabric) -> None:
        self._authority_discovery=authority_discovery; self._anti_bypass=anti_bypass; self._adapter_fabric=adapter_fabric
    def execute(self, *, selection: SoftwareSelectionRequest, composition: OCSCompositionResult, discovery: AuthorityAwareDiscoveryResult, action_receipt: ActionCognitiveReceipt, runtime_context: RuntimeExecutionContext, payload: Mapping[str, object], input_schema_version: str, expected_output_schema_version: str) -> GovernedSoftwareExecutionResult:
        selection.validate(); capability=discovery.capability_discovery.selected_capability; authority=discovery.authority_receipt
        if composition.mission_id != selection.mission_id or discovery.capability_discovery.mission_id != selection.mission_id: raise GovernedSoftwareExecutionError("governed_execution_mission_mismatch")
        if composition.composition_receipt != selection.composition_receipt: raise GovernedSoftwareExecutionError("governed_execution_composition_receipt_mismatch")
        if discovery.governed_discovery_receipt != selection.governed_discovery_receipt: raise GovernedSoftwareExecutionError("governed_execution_discovery_receipt_mismatch")
        if capability.capability_id != selection.capability_id: raise GovernedSoftwareExecutionError("governed_execution_capability_mismatch")
        if action_receipt.receipt_id != selection.action_receipt_id: raise GovernedSoftwareExecutionError("governed_execution_action_receipt_mismatch")
        if authority.receipt_id != selection.authority_receipt_id: raise GovernedSoftwareExecutionError("governed_execution_authority_receipt_mismatch")
        if not self._authority_discovery.verify_authority_receipt(authority, action_receipt=action_receipt): raise GovernedSoftwareExecutionError("governed_execution_invalid_authority")
        if dict(composition.capability_assignments).get(selection.capability_id) != selection.ocs_id: raise GovernedSoftwareExecutionError("governed_execution_ocs_assignment_mismatch")
        selected={r.ocs_id:r for r in composition.selected_ocs}; ocs=selected.get(selection.ocs_id)
        if ocs is None or not ocs.healthy: raise GovernedSoftwareExecutionError("governed_execution_ocs_unavailable")
        if selection.capability_id not in ocs.supported_capabilities: raise GovernedSoftwareExecutionError("governed_execution_ocs_capability_mismatch")
        if runtime_context.mission_id != selection.mission_id: raise GovernedSoftwareExecutionError("governed_execution_runtime_mission_mismatch")
        if runtime_context.ocs_id != selection.ocs_id: raise GovernedSoftwareExecutionError("governed_execution_runtime_ocs_mismatch")
        if runtime_context.capability_id != capability.capability_id: raise GovernedSoftwareExecutionError("governed_execution_runtime_capability_mismatch")
        if runtime_context.capability_version != capability.capability_version: raise GovernedSoftwareExecutionError("governed_execution_runtime_capability_version_mismatch")
        if runtime_context.adapter_version != capability.adapter_version: raise GovernedSoftwareExecutionError("governed_execution_runtime_adapter_version_mismatch")
        context=AdapterInvocationContext(mission_id=selection.mission_id,action_receipt_id=action_receipt.receipt_id,authority_receipt_id=authority.receipt_id,capability_discovery_receipt=discovery.capability_discovery.discovery_receipt,input_schema_version=input_schema_version,expected_output_schema_version=expected_output_schema_version)
        def invoke(): return self._adapter_fabric.execute(discovery.capability_discovery,context,payload)
        try: governed=self._anti_bypass.execute(action_receipt,context=runtime_context,executor=invoke)
        except Exception as exc: raise GovernedSoftwareExecutionError("governed_execution_denied_or_failed") from exc
        response,adapter_receipt=governed.result
        receipt=self._digest({"mission_id":selection.mission_id,"capability_id":selection.capability_id,"ocs_id":selection.ocs_id,"composition_receipt":selection.composition_receipt,"governed_discovery_receipt":selection.governed_discovery_receipt,"action_receipt_id":selection.action_receipt_id,"authority_receipt_id":selection.authority_receipt_id,"adapter_execution_receipt":adapter_receipt.execution_receipt,"status":adapter_receipt.status})
        return GovernedSoftwareExecutionResult(selection.mission_id,selection.capability_id,selection.ocs_id,adapter_receipt.adapter_id,adapter_receipt.adapter_version,adapter_receipt.status,adapter_receipt,receipt,response)
    @staticmethod
    def _digest(payload: object) -> str:
        return sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=list).encode()).hexdigest()
