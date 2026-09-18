from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .adapter_fabric import AdapterHealth, AdapterRecord, InstitutionalAdapterFabric
from .governed_execution import GovernedSoftwareExecutor, SoftwareSelectionRequest
from .ocs_composition import GovernedOCSComposer, InstitutionalOCSRegistry, OCSCompositionRequest, OCSRecord
from .runtime_anti_bypass import RuntimeAntiBypassGateway, RuntimeExecutionContext
from . import phase_d2_adversarial_semantic as base

LOGGER = logging.getLogger("coi15.phase_d2.v2")
PROGRAM = base.PROGRAM
MISSION = base.MISSION
ARTIFACT_DIR = Path(os.getenv("COI15_QUALIFICATION_DIR", "/tmp/coi15-operational-qualification"))
EVIDENCE_PATH = ARTIFACT_DIR / "phase_d2_evidence.json"


def _build_governed_timeout_context(ctx: dict[str, Any], effects: list[dict[str, Any]]):
    action = base._issue_action(ctx, digest="d2-timeout-double-execution")
    authority_id = "auth-d2-timeout"
    base._register_grant(ctx, authority_id)
    discovery = ctx["authority"].discover(
        capability_id="github", required_schema_version="schema-v1", action_receipt=action,
        authority_id=authority_id, operation_class="CLASS_3",
    )
    ocs_registry = InstitutionalOCSRegistry()
    ocs_registry.register(OCSRecord(
        ocs_id="NOESIS", ocs_version="v1", identity_ref="identity:NOESIS",
        constitution_ref="constitution:NOESIS", cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        runtime_endpoint="operational://coi15-phase-d2", supported_capabilities=("github",),
        authority_requirements=("qualification:write",),
        required_receipts=("MISSION_COGNITIVE_RECEIPT", "ACTION_COGNITIVE_RECEIPT", "AUTHORITY_RECEIPT"),
    ))
    composition = GovernedOCSComposer(ocs_registry).compose(
        OCSCompositionRequest(
            mission_id=MISSION, plan_hash="plan:d2-timeout-double-execution", required_capabilities=("github",),
            governed_discovery_receipts=(discovery.governed_discovery_receipt,),
        ), [discovery],
    )
    effect_started = threading.Event()
    release_executor = threading.Event()
    adapter_fabric = InstitutionalAdapterFabric()

    def handler(payload: Any) -> dict[str, Any]:
        effects.append({"scenario": "TIMEOUT_DOUBLE_EXECUTION", "payload": dict(payload)})
        effect_started.set()
        release_executor.wait(timeout=5)
        return {"recorded": True, "effect_index": len(effects)}

    adapter_fabric.register(AdapterRecord(
        adapter_id="github-adapter", adapter_version="adapter-v1", capability_id="github",
        capability_version="v1", endpoint="qualification://phase-d2",
        input_schema_version="schema-v1", output_schema_version="out-v1", health=AdapterHealth.HEALTHY,
    ), handler)
    executor = GovernedSoftwareExecutor(
        authority_discovery=ctx["authority"],
        anti_bypass=RuntimeAntiBypassGateway(action_issuer=ctx["action_issuer"]),
        adapter_fabric=adapter_fabric,
    )
    selection = SoftwareSelectionRequest(
        MISSION, "github", "NOESIS", composition.composition_receipt,
        discovery.governed_discovery_receipt, action.receipt_id, discovery.authority_receipt.receipt_id,
    )
    runtime_context = RuntimeExecutionContext(
        MISSION, "NOESIS", "noesis-d2-1", 1, "github", "v1", "adapter-v1",
        "d2-timeout-double-execution", "d2-state-0", "policy-v1",
    )
    return action, discovery, composition, executor, selection, runtime_context, effect_started, release_executor


def _scenario_timeout_double_execution(ctx: dict[str, Any], effects: list[dict[str, Any]]):
    before = len(effects)
    (action, discovery, composition, executor, selection, runtime_context,
     effect_started, release_executor) = _build_governed_timeout_context(ctx, effects)
    first: dict[str, Any] = {}

    def first_execution() -> None:
        try:
            result = executor.execute(
                selection=selection, composition=composition, discovery=discovery,
                action_receipt=action, runtime_context=runtime_context,
                payload={"qualification": "COI15-D2", "scenario": "timeout"},
                input_schema_version="schema-v1", expected_output_schema_version="out-v1",
            )
            first.update({"outcome": "EXECUTED_CONFIRMED", "receipt": result.governed_execution_receipt})
        except Exception as exc:
            first.update({"outcome": "FAILED", "error": f"{type(exc).__name__}:{exc}"})

    worker = threading.Thread(target=first_execution, daemon=True)
    worker.start()
    effect_seen = effect_started.wait(timeout=5)
    worker.join(timeout=0.02)
    execution_unknown = effect_seen and worker.is_alive()
    retry_error = ""
    retry_before = len(effects)
    try:
        executor.execute(
            selection=selection, composition=composition, discovery=discovery,
            action_receipt=action, runtime_context=runtime_context,
            payload={"qualification": "COI15-D2", "scenario": "blind-retry"},
            input_schema_version="schema-v1", expected_output_schema_version="out-v1",
        )
    except Exception as exc:
        retry_error = f"{type(exc).__name__}:{exc}"
    retry_after = len(effects)
    release_executor.set()
    worker.join(timeout=5)
    after = len(effects)
    verified = (
        execution_unknown and retry_after == retry_before and after - before == 1
        and "governed_execution_denied_or_failed" in retry_error
        and first.get("outcome") == "EXECUTED_CONFIRMED" and not worker.is_alive()
    )
    return base._evidence("TIMEOUT_DOUBLE_EXECUTION", before, after, {
        "first_effect_observed_before_timeout": effect_seen,
        "caller_state_after_timeout": "EXECUTION_UNKNOWN" if execution_unknown else "NOT_UNKNOWN",
        "blind_retry_attempted": True,
        "blind_retry_error": retry_error,
        "retry_effect_delta": retry_after - retry_before,
        "reconciliation_required": execution_unknown,
        "first_execution_final": first,
        "semantic_sequence": "governed_execution->effect_occurs->caller_timeout/unknown->blind_retry->denied->reconcile->single_effect",
    }, verified)


def run_phase_d2_semantic_qualification() -> dict[str, Any]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = base._base_context()
    effects: list[dict[str, Any]] = []
    scenarios = [
        base._scenario_revoked_authority(ctx, effects),
        base._scenario_concurrent_receipt(ctx, effects),
        _scenario_timeout_double_execution(ctx, effects),
    ]
    evidence = {
        "program": PROGRAM,
        "event": "PHASE_D2_ADVERSARIAL_SEMANTIC_COMPLETE",
        "runtime_pid": os.getpid(),
        "scenario_count": len(scenarios),
        "all_semantic_scenarios_verified": all(item.scenario_verified for item in scenarios),
        "total_material_effects": len(effects),
        "scenarios": [asdict(item) for item in scenarios],
        "assurance_disposition_changed": False,
        "founder_promotion_executed": False,
    }
    evidence["qualification_receipt"] = base._digest(evidence)
    with EVIDENCE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(evidence, fh, sort_keys=True, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    LOGGER.warning("COI15_PHASE_D2_EVIDENCE %s", json.dumps(evidence, sort_keys=True, default=str))
    if not evidence["all_semantic_scenarios_verified"]:
        raise RuntimeError("COI15_PHASE_D2_SEMANTIC_QUALIFICATION_FAILED")
    return evidence


def read_phase_d2_evidence() -> dict[str, Any]:
    if not EVIDENCE_PATH.exists():
        return {"status": "not_ready", "program": PROGRAM}
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
