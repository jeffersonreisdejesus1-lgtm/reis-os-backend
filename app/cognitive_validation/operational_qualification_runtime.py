from __future__ import annotations

import json
import logging
import multiprocessing as mp
import os
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from fastapi import FastAPI

from .action_receipt import ActionCognitiveReceiptIssuer
from .adapter_fabric import AdapterHealth, AdapterInvocationContext, AdapterRecord, InstitutionalAdapterFabric
from .adversarial_failure_bypass import AdversarialFailureBypassQualifier
from .authority_aware_discovery import AuthorityAwareCapabilityDiscovery, AuthorityGrant, InstitutionalAuthorityRegistry
from .bootstrap_binding import BootstrapCognitiveBinding
from .capability_fabric import CapabilityHealth, CapabilityRecord, InstitutionalCapabilityFabric
from .contracts import CognitiveValidationContract, enforce_cognitive_contract
from .governed_execution import GovernedSoftwareExecutor, SoftwareSelectionRequest
from .mission_receipt import MissionCognitiveReceiptIssuer
from .observation_evidence_state import EffectObservation, InstitutionalStateStore, ObservationEvidenceStateUpdater
from .ocs_composition import GovernedOCSComposer, InstitutionalOCSRegistry, OCSCompositionRequest, OCSRecord
from .operational_learning_loop import ClosedOperationalLearningLoop
from .persistent_learning_runtime import PersistentClosedOperationalLearningRuntime, PersistentOperationalLearningStore
from .receipt_provenance import ReceiptProvenanceVerifier
from .runtime_adversarial_evidence import RuntimeAdversarialEvidenceLedger
from .runtime_anti_bypass import RuntimeAntiBypassGateway, RuntimeExecutionContext
from .universal_entrypoint import CognitiveMissionContext, UniversalCognitiveEntrypoint

LOGGER = logging.getLogger("coi15.operational_qualification")
PROGRAM = "REIS-OS-COGNITIVE-OPERATIONAL-INTEGRATION-001"
MISSION_N = "COI15-QUAL-MISSION-N"
MISSION_N1 = "COI15-QUAL-MISSION-N1"
ARTIFACT_DIR = Path(os.getenv("COI15_QUALIFICATION_DIR", "/tmp/coi15-operational-qualification"))
DB_PATH = ARTIFACT_DIR / "learning.sqlite3"
EVIDENCE_PATH = ARTIFACT_DIR / "evidence.json"
EFFECT_PATH = ARTIFACT_DIR / "material_effect.jsonl"

app = FastAPI(title="REIS OS COI15 Operational Qualification Runtime")


def _secret(label: str) -> bytes:
    root = os.getenv("COI15_QUALIFICATION_SECRET", "")
    if not root:
        raise RuntimeError("COI15_QUALIFICATION_SECRET_REQUIRED")
    return f"{root}:{label}".encode("utf-8")


def _emit(event: str, payload: dict[str, Any]) -> None:
    record = {"program": PROGRAM, "event": event, **payload}
    LOGGER.warning("COI15_OPERATIONAL_EVIDENCE %s", json.dumps(record, sort_keys=True, default=str))


def _next_mission_worker(db_path: str, learning_receipt: str, queue: Any) -> None:
    try:
        store = PersistentOperationalLearningStore(db_path)
        runtime = PersistentClosedOperationalLearningRuntime(store=store)
        plan = runtime.begin_distinct_next_mission(
            source_mission_id=MISSION_N,
            next_mission_id=MISSION_N1,
            expected_learning_receipt=learning_receipt,
        )
        store.close()
        queue.put({"ok": True, "pid": os.getpid(), "plan": asdict(plan)})
    except Exception as exc:  # operational proof boundary
        queue.put({"ok": False, "pid": os.getpid(), "error": f"{type(exc).__name__}:{exc}"})


def _build_operational_chain() -> dict[str, Any]:
    now = 100.0
    clock = lambda: now
    mission_issuer = MissionCognitiveReceiptIssuer(
        signing_secret=_secret("mission"), clock=clock, nonce_factory=lambda: "op-mission-nonce"
    )
    action_issuer = ActionCognitiveReceiptIssuer(
        signing_secret=_secret("action"), mission_issuer=mission_issuer, clock=clock,
        nonce_factory=lambda: "op-action-nonce",
    )
    entry = UniversalCognitiveEntrypoint()
    proposal = entry.enter(CognitiveMissionContext(
        mission_id=MISSION_N, ocs_id="NOESIS", ocs_instance_id="noesis-op-1", generation=1,
        intent="COI15 authoritative operational qualification", state_revision="state-r1",
    ))
    binding = BootstrapCognitiveBinding(
        binding_id="coi15-operational-binding", mission_id=MISSION_N, ocs_id="NOESIS",
        ocs_instance_id="noesis-op-1", generation=1,
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT", brain_path=proposal.brain_version,
        authority_ref="authority:coi15-operational", state_namespace="state:coi15-operational",
        memory_namespace="memory:coi15-operational",
    )
    mission = mission_issuer.issue(
        binding, intent="COI15 authoritative operational qualification",
        state_revision="state-r1", state_hash="state-0", cognition_cycle_id="cycle-op-1",
    )
    action = action_issuer.issue(
        mission, plan_hash="plan-op-1", action_digest="record-controlled-operational-effect",
        capability_id="github", capability_version="v1", adapter_version="adapter-v1",
        authority_requirements=("qualification:write",), state_hash="state-0", policy_version="policy-v1",
    )
    capability_fabric = InstitutionalCapabilityFabric([CapabilityRecord(
        capability_id="github", capability_version="v1", adapter_id="github-adapter",
        adapter_version="adapter-v1", endpoint="qualification://material-effect",
        schema_version="schema-v1", health=CapabilityHealth.HEALTHY,
        authorized_missions=(MISSION_N,),
    )])
    authority_registry = InstitutionalAuthorityRegistry()
    authority_registry.register(AuthorityGrant(
        authority_id="auth-op-1", mission_id=MISSION_N, ocs_id="NOESIS", capability_id="github",
        adapter_version="adapter-v1", operation_class="CLASS_3", policy_version="policy-v1",
        authority_requirements=("qualification:write",), valid_from=90.0, valid_until=200.0,
    ))
    authority = AuthorityAwareCapabilityDiscovery(
        capability_fabric=capability_fabric, authority_registry=authority_registry,
        action_issuer=action_issuer, signing_secret=_secret("authority"), clock=clock,
        nonce_factory=lambda: "op-authority-nonce",
    )
    discovery = authority.discover(
        capability_id="github", required_schema_version="schema-v1", action_receipt=action,
        authority_id="auth-op-1", operation_class="CLASS_3",
    )
    ocs_registry = InstitutionalOCSRegistry()
    ocs_registry.register(OCSRecord(
        ocs_id="NOESIS", ocs_version="v1", identity_ref="identity:NOESIS",
        constitution_ref="constitution:NOESIS", cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        runtime_endpoint="operational://coi15", supported_capabilities=("github",),
        authority_requirements=("qualification:write",),
        required_receipts=("MISSION_COGNITIVE_RECEIPT", "ACTION_COGNITIVE_RECEIPT", "AUTHORITY_RECEIPT"),
    ))
    composition = GovernedOCSComposer(ocs_registry).compose(
        OCSCompositionRequest(
            mission_id=MISSION_N, plan_hash="plan-op-1", required_capabilities=("github",),
            governed_discovery_receipts=(discovery.governed_discovery_receipt,),
        ),
        [discovery],
    )
    effects: list[dict[str, Any]] = []
    adapter_fabric = InstitutionalAdapterFabric()

    def handler(payload: Any) -> dict[str, Any]:
        event = {"mission_id": MISSION_N, "payload": dict(payload), "effect_index": len(effects) + 1}
        effects.append(event)
        with EFFECT_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return {"recorded": True, "effect_index": len(effects)}

    adapter_fabric.register(AdapterRecord(
        adapter_id="github-adapter", adapter_version="adapter-v1", capability_id="github",
        capability_version="v1", endpoint="qualification://material-effect",
        input_schema_version="schema-v1", output_schema_version="out-v1", health=AdapterHealth.HEALTHY,
    ), handler)
    anti_bypass = RuntimeAntiBypassGateway(action_issuer=action_issuer)
    executor = GovernedSoftwareExecutor(
        authority_discovery=authority, anti_bypass=anti_bypass, adapter_fabric=adapter_fabric
    )
    selection = SoftwareSelectionRequest(
        MISSION_N, "github", "NOESIS", composition.composition_receipt,
        discovery.governed_discovery_receipt, action.receipt_id, discovery.authority_receipt.receipt_id,
    )
    runtime_context = RuntimeExecutionContext(
        MISSION_N, "NOESIS", "noesis-op-1", 1, "github", "v1", "adapter-v1",
        "record-controlled-operational-effect", "state-0", "policy-v1",
    )
    execution = executor.execute(
        selection=selection, composition=composition, discovery=discovery,
        action_receipt=action, runtime_context=runtime_context,
        payload={"qualification": "COI15", "outcome": "FAILURE"},
        input_schema_version="schema-v1", expected_output_schema_version="out-v1",
    )
    observation = EffectObservation(
        mission_id=MISSION_N, capability_id="github", ocs_id="NOESIS",
        governed_execution_receipt=execution.governed_execution_receipt,
        execution_status=execution.execution_status,
        observed_effect={"effect_file": str(EFFECT_PATH), "effect_count": len(effects), "outcome": "FAILURE"},
    )
    coi11 = ObservationEvidenceStateUpdater(state_store=InstitutionalStateStore()).qualify_and_update(
        execution=execution, observation=observation,
        state_delta={"last_operational_effect": execution.governed_execution_receipt, "outcome": "FAILURE"},
    )
    previous = ClosedOperationalLearningLoop.initial_plan(
        mission_id=MISSION_N, capability_id="github", state_hash="state-0"
    )
    store = PersistentOperationalLearningStore(DB_PATH)
    learning_runtime = PersistentClosedOperationalLearningRuntime(store=store)
    learning = learning_runtime.close_loop_and_commit(
        previous_plan=previous, coi11_result=coi11,
        candidate_capabilities=("github", "software_factory"), outcome="FAILURE",
    )
    store.close()
    verifier = ReceiptProvenanceVerifier(
        mission_issuer=mission_issuer, action_issuer=action_issuer, authority_discovery=authority
    )
    provenance = verifier.verify(
        mission=mission, action=action, authority=discovery.authority_receipt,
        execution=execution, coi11=coi11, learning=learning, verification_time=100.0,
    )
    return {
        "mission_issuer": mission_issuer, "action_issuer": action_issuer,
        "authority": authority, "authority_registry": authority_registry,
        "capability_fabric": capability_fabric, "adapter_fabric": adapter_fabric,
        "anti_bypass": anti_bypass, "mission": mission, "action": action,
        "discovery": discovery, "composition": composition, "execution": execution,
        "coi11": coi11, "learning": learning, "provenance": provenance,
        "runtime_context": runtime_context, "effects": effects, "verifier": verifier,
    }


def _run_adversarial(chain: dict[str, Any]) -> dict[str, Any]:
    ledger = RuntimeAdversarialEvidenceLedger()
    probes = []
    effects = chain["effects"]
    effect_counter = lambda: len(effects)
    action = chain["action"]
    runtime_context = chain["runtime_context"]
    anti_bypass = chain["anti_bypass"]
    capability_fabric = chain["capability_fabric"]
    adapter_fabric = chain["adapter_fabric"]
    discovery = chain["discovery"]
    execution = chain["execution"]
    coi11 = chain["coi11"]
    learning = chain["learning"]
    verifier = chain["verifier"]

    def probe(attack_class: str, action_name: str, attack: Callable[[], object]) -> None:
        probes.append(ledger.execute_probe(
            probe_id=f"op-{len(probes)+1:02d}", attack_class=attack_class,
            attempted_action=action_name, attack=attack, effect_counter=effect_counter,
        ))

    probe("DIRECT_SOFTWARE_BYPASS", "execute without cognitive receipt",
          lambda: anti_bypass.execute(None, context=runtime_context, executor=lambda: effects.append({"unsafe": True})))
    probe("FAKE_RECEIPT", "forged action signature",
          lambda: anti_bypass.execute(replace(action, signature="forged"), context=runtime_context,
                                      executor=lambda: effects.append({"unsafe": True})))
    probe("EXPIRED_RECEIPT", "expired action receipt",
          lambda: anti_bypass.execute(replace(action, expires_at=0.0), context=runtime_context,
                                      executor=lambda: effects.append({"unsafe": True})))
    probe("WRONG_CONTEXT_RECEIPT", "wrong mission context",
          lambda: anti_bypass.execute(action, context=replace(runtime_context, mission_id="wrong-mission"),
                                      executor=lambda: effects.append({"unsafe": True})))
    probe("REPLAY", "replay consumed action receipt",
          lambda: anti_bypass.execute(action, context=runtime_context, executor=lambda: effects.append({"unsafe": True})))
    probe("CAPABILITY_WITHOUT_AUTHORITY", "capability for unauthorized mission",
          lambda: capability_fabric.discover("github", mission_id="unauthorized", required_schema_version="schema-v1"))
    probe("BRAIN_UNAVAILABLE", "cognitive entry with unavailable brain",
          lambda: UniversalCognitiveEntrypoint(brain=object()).enter(CognitiveMissionContext(
              mission_id="brain-fail", ocs_id="NOESIS", ocs_instance_id="n", generation=1, intent="probe")))
    missing_adapter = InstitutionalAdapterFabric()
    probe("ADAPTER_UNAVAILABLE", "missing adapter",
          lambda: missing_adapter.execute(discovery.capability_discovery, AdapterInvocationContext(
              mission_id=MISSION_N, action_receipt_id=action.receipt_id,
              authority_receipt_id=discovery.authority_receipt.receipt_id,
              capability_discovery_receipt=discovery.capability_discovery.discovery_receipt,
              input_schema_version="schema-v1", expected_output_schema_version="out-v1"), {}))
    probe("HALLUCINATED_CAPABILITY", "unregistered capability",
          lambda: capability_fabric.discover("hallucinated", mission_id=MISSION_N, required_schema_version="schema-v1"))
    probe("STALE_STATE", "stale runtime state",
          lambda: anti_bypass.execute(action, context=replace(runtime_context, state_hash="stale-state"),
                                      executor=lambda: effects.append({"unsafe": True})))
    probe("SCHEMA_MISMATCH", "adapter schema mismatch",
          lambda: adapter_fabric.execute(discovery.capability_discovery, AdapterInvocationContext(
              mission_id=MISSION_N, action_receipt_id=action.receipt_id,
              authority_receipt_id=discovery.authority_receipt.receipt_id,
              capability_discovery_receipt=discovery.capability_discovery.discovery_receipt,
              input_schema_version="wrong-schema", expected_output_schema_version="out-v1"), {}))
    probe("REVOKED_AUTHORITY", "revoked authority",
          lambda: chain["authority_registry"].revoke("missing-authority"))
    probe("SUCCESS_WITHOUT_EVIDENCE", "success without state delta",
          lambda: ObservationEvidenceStateUpdater(state_store=InstitutionalStateStore()).qualify_and_update(
              execution=execution,
              observation=EffectObservation(MISSION_N, "github", "NOESIS", execution.governed_execution_receipt,
                                            execution.execution_status, {"observed": True}), state_delta={}))
    probe("EXECUTION_UNKNOWN", "unknown execution status",
          lambda: ObservationEvidenceStateUpdater(state_store=InstitutionalStateStore()).qualify_and_update(
              execution=replace(execution, execution_status="EXECUTION_UNKNOWN"),
              observation=EffectObservation(MISSION_N, "github", "NOESIS", execution.governed_execution_receipt,
                                            "EXECUTION_UNKNOWN", {"observed": True}), state_delta={"x": 1}))
    probe("PARTIAL_EFFECT", "partial execution status",
          lambda: ObservationEvidenceStateUpdater(state_store=InstitutionalStateStore()).qualify_and_update(
              execution=replace(execution, execution_status="EXECUTED_PARTIAL"),
              observation=EffectObservation(MISSION_N, "github", "NOESIS", execution.governed_execution_receipt,
                                            "EXECUTED_PARTIAL", {"observed": True}), state_delta={"x": 1}))
    probe("CONCURRENT_RECEIPT_CONFLICT", "second consume of same receipt",
          lambda: anti_bypass.execute(action, context=runtime_context, executor=lambda: effects.append({"unsafe": True})))
    probe("TIMEOUT_DOUBLE_EXECUTION", "blind retry after consumed receipt",
          lambda: anti_bypass.execute(action, context=runtime_context, executor=lambda: effects.append({"unsafe": True})))
    probe("CONSTITUTIONAL_SELF_MODIFICATION", "rewrite constitutional authority invariant",
          lambda: enforce_cognitive_contract(CognitiveValidationContract(adaptation_may_rewrite_constitution=True)))
    forged = replace(coi11, evidence=replace(coi11.evidence, evidence_receipt="forged"))
    probe("FALSIFIED_EVIDENCE", "forged evidence receipt",
          lambda: verifier.verify(mission=chain["mission"], action=action,
                                  authority=discovery.authority_receipt, execution=execution,
                                  coi11=forged, learning=learning, verification_time=100.0))

    result = AdversarialFailureBypassQualifier().qualify(probes)
    return {
        "attack_count": len(result.covered_attack_classes),
        "covered_attack_classes": list(result.covered_attack_classes),
        "qualification_receipt": result.qualification_receipt,
        "events": [asdict(item) for item in ledger.events],
    }


def run_qualification() -> dict[str, Any]:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (DB_PATH, EVIDENCE_PATH, EFFECT_PATH):
        if path.exists():
            path.unlink()
    chain = _build_operational_chain()
    adversarial = _run_adversarial(chain)

    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    child = ctx.Process(target=_next_mission_worker, args=(str(DB_PATH), chain["learning"].learning_receipt, queue))
    child.start()
    child.join(20)
    if child.is_alive():
        child.terminate(); child.join(); raise RuntimeError("MISSION_N1_PROCESS_TIMEOUT")
    cross_mission = queue.get(timeout=2)
    if not cross_mission.get("ok"):
        raise RuntimeError(f"MISSION_N1_FAILED:{cross_mission}")

    evidence = {
        "program": PROGRAM,
        "runtime_pid": os.getpid(),
        "mission_n": MISSION_N,
        "mission_n1": MISSION_N1,
        "mission_receipt_id": chain["mission"].receipt_id,
        "action_receipt_id": chain["action"].receipt_id,
        "authority_receipt_id": chain["discovery"].authority_receipt.receipt_id,
        "governed_execution_receipt": chain["execution"].governed_execution_receipt,
        "evidence_receipt": chain["coi11"].evidence.evidence_receipt,
        "state_hash": chain["coi11"].state_snapshot.state_hash,
        "learning_receipt": chain["learning"].learning_receipt,
        "lineage_receipt": chain["provenance"].lineage_receipt,
        "route_n": chain["learning"].previous_plan.selected_capability_id,
        "learned_route": chain["learning"].next_plan.selected_capability_id,
        "cross_mission": cross_mission,
        "adversarial": adversarial,
        "effect_file": str(EFFECT_PATH),
        "effect_count": len(chain["effects"]),
        "assurance_disposition_changed": False,
        "founder_promotion_executed": False,
    }
    with EVIDENCE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(evidence, fh, sort_keys=True, indent=2)
        fh.flush(); os.fsync(fh.fileno())
    _emit("QUALIFICATION_COMPLETE", evidence)
    return evidence


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "program": PROGRAM,
        "runtime": "COI15_OPERATIONAL_QUALIFICATION",
        "evidence_available": EVIDENCE_PATH.exists(),
    }


@app.get("/evidence")
def evidence() -> dict[str, Any]:
    if not EVIDENCE_PATH.exists():
        return {"status": "not_ready", "program": PROGRAM}
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_qualification()
    print(json.dumps({"event": "COI15_OPERATIONAL_QUALIFICATION_COMPLETE", "evidence": result}, sort_keys=True))
