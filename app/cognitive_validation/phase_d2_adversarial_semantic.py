from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .action_receipt import ActionCognitiveReceiptIssuer
from .adapter_fabric import AdapterHealth, AdapterRecord, InstitutionalAdapterFabric
from .authority_aware_discovery import (
    AuthorityAwareCapabilityDiscovery,
    AuthorityGrant,
    InstitutionalAuthorityRegistry,
)
from .bootstrap_binding import BootstrapCognitiveBinding
from .capability_fabric import CapabilityHealth, CapabilityRecord, InstitutionalCapabilityFabric
from .governed_execution import GovernedSoftwareExecutor, SoftwareSelectionRequest
from .mission_receipt import MissionCognitiveReceiptIssuer
from .ocs_composition import GovernedOCSComposer, InstitutionalOCSRegistry, OCSCompositionRequest, OCSRecord
from .runtime_anti_bypass import RuntimeAntiBypassGateway, RuntimeExecutionContext
from .universal_entrypoint import CognitiveMissionContext, UniversalCognitiveEntrypoint

LOGGER = logging.getLogger("coi15.phase_d2")
PROGRAM = "REIS-OS-COGNITIVE-OPERATIONAL-INTEGRATION-001"
MISSION = "COI15-PHASE-D2-MISSION"
ARTIFACT_DIR = Path(os.getenv("COI15_QUALIFICATION_DIR", "/tmp/coi15-operational-qualification"))
EVIDENCE_PATH = ARTIFACT_DIR / "phase_d2_evidence.json"


@dataclass(frozen=True, slots=True)
class SemanticScenarioEvidence:
    attack_class: str
    scenario_verified: bool
    effect_before: int
    effect_after: int
    effect_delta: int
    observations: dict[str, Any]
    evidence_ref: str


def _secret(label: str) -> bytes:
    root = os.getenv("COI15_QUALIFICATION_SECRET", "")
    if not root:
        raise RuntimeError("COI15_QUALIFICATION_SECRET_REQUIRED")
    return f"{root}:phase-d2:{label}".encode()


def _digest(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _evidence(attack_class: str, before: int, after: int, observations: dict[str, Any], verified: bool) -> SemanticScenarioEvidence:
    payload = {
        "attack_class": attack_class,
        "scenario_verified": verified,
        "effect_before": before,
        "effect_after": after,
        "effect_delta": after - before,
        "observations": observations,
    }
    return SemanticScenarioEvidence(
        attack_class=attack_class,
        scenario_verified=verified,
        effect_before=before,
        effect_after=after,
        effect_delta=after - before,
        observations=observations,
        evidence_ref="phase-d2-evidence:" + _digest(payload),
    )


def _base_context() -> dict[str, Any]:
    now = 100.0
    clock = lambda: now
    mission_issuer = MissionCognitiveReceiptIssuer(
        signing_secret=_secret("mission"), clock=clock, nonce_factory=lambda: "d2-mission-nonce"
    )
    action_issuer = ActionCognitiveReceiptIssuer(
        signing_secret=_secret("action"), mission_issuer=mission_issuer, clock=clock,
        nonce_factory=lambda: os.urandom(8).hex(),
    )
    proposal = UniversalCognitiveEntrypoint().enter(CognitiveMissionContext(
        mission_id=MISSION, ocs_id="NOESIS", ocs_instance_id="noesis-d2-1", generation=1,
        intent="COI15 Phase D2 adversarial semantic qualification", state_revision="d2-state-r1",
    ))
    binding = BootstrapCognitiveBinding(
        binding_id="coi15-phase-d2-binding", mission_id=MISSION, ocs_id="NOESIS",
        ocs_instance_id="noesis-d2-1", generation=1,
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT", brain_path=proposal.brain_version,
        authority_ref="authority:coi15-phase-d2", state_namespace="state:coi15-phase-d2",
        memory_namespace="memory:coi15-phase-d2",
    )
    mission = mission_issuer.issue(
        binding, intent="COI15 Phase D2 adversarial semantic qualification",
        state_revision="d2-state-r1", state_hash="d2-state-0", cognition_cycle_id="d2-cycle-1",
    )
    capability_fabric = InstitutionalCapabilityFabric([CapabilityRecord(
        capability_id="github", capability_version="v1", adapter_id="github-adapter",
        adapter_version="adapter-v1", endpoint="qualification://phase-d2",
        schema_version="schema-v1", health=CapabilityHealth.HEALTHY,
        authorized_missions=(MISSION,),
    )])
    registry = InstitutionalAuthorityRegistry()
    authority = AuthorityAwareCapabilityDiscovery(
        capability_fabric=capability_fabric, authority_registry=registry,
        action_issuer=action_issuer, signing_secret=_secret("authority"), clock=clock,
        nonce_factory=lambda: os.urandom(8).hex(),
    )
    return {
        "clock": clock,
        "mission": mission,
        "action_issuer": action_issuer,
        "capability_fabric": capability_fabric,
        "authority_registry": registry,
        "authority": authority,
    }


def _issue_action(ctx: dict[str, Any], *, digest: str):
    return ctx["action_issuer"].issue(
        ctx["mission"], plan_hash=f"plan:{digest}", action_digest=digest,
        capability_id="github", capability_version="v1", adapter_version="adapter-v1",
        authority_requirements=("qualification:write",), state_hash="d2-state-0", policy_version="policy-v1",
    )


def _register_grant(ctx: dict[str, Any], authority_id: str) -> None:
    ctx["authority_registry"].register(AuthorityGrant(
        authority_id=authority_id, mission_id=MISSION, ocs_id="NOESIS", capability_id="github",
        adapter_version="adapter-v1", operation_class="CLASS_3", policy_version="policy-v1",
        authority_requirements=("qualification:write",), valid_from=90.0, valid_until=200.0,
    ))


def _scenario_revoked_authority(ctx: dict[str, Any], effects: list[dict[str, Any]]) -> SemanticScenarioEvidence:
    before = len(effects)
    action = _issue_action(ctx, digest="d2-revoked-authority")
    authority_id = "auth-d2-revoked"
    _register_grant(ctx, authority_id)
    pre = ctx["authority"].discover(
        capability_id="github", required_schema_version="schema-v1", action_receipt=action,
        authority_id=authority_id, operation_class="CLASS_3",
    )
    pre_valid = ctx["authority"].verify_authority_receipt(pre.authority_receipt, action_receipt=action, now=100.0)
    ctx["authority_registry"].revoke(authority_id)
    post_receipt_valid = ctx["authority"].verify_authority_receipt(pre.authority_receipt, action_receipt=action, now=100.0)
    error = ""
    try:
        ctx["authority"].discover(
            capability_id="github", required_schema_version="schema-v1", action_receipt=action,
            authority_id=authority_id, operation_class="CLASS_3",
        )
    except Exception as exc:
        error = f"{type(exc).__name__}:{exc}"
    after = len(effects)
    verified = pre_valid and not post_receipt_valid and error.endswith(":authority_revoked") and after == before
    return _evidence("REVOKED_AUTHORITY", before, after, {
        "authority_id": authority_id,
        "pre_revoke_discovery_receipt": pre.governed_discovery_receipt,
        "pre_revoke_authority_valid": pre_valid,
        "post_revoke_prior_receipt_valid": post_receipt_valid,
        "post_revoke_discovery_error": error,
        "semantic_sequence": "valid_authority->verified->revoke_exact_grant->rediscover->authority_revoked",
    }, verified)


def _scenario_concurrent_receipt(ctx: dict[str, Any], effects: list[dict[str, Any]]) -> SemanticScenarioEvidence:
    before = len(effects)
    action = _issue_action(ctx, digest="d2-concurrent-receipt")
    anti_bypass = RuntimeAntiBypassGateway(action_issuer=ctx["action_issuer"])
    runtime_context = RuntimeExecutionContext(
        MISSION, "NOESIS", "noesis-d2-1", 1, "github", "v1", "adapter-v1",
        "d2-concurrent-receipt", "d2-state-0", "policy-v1",
    )
    barrier = threading.Barrier(3)
    effect_lock = threading.Lock()
    results: list[dict[str, Any]] = []
    results_lock = threading.Lock()

    def material_effect(contender: str) -> dict[str, Any]:
        with effect_lock:
            effects.append({"scenario": "CONCURRENT_RECEIPT_CONFLICT", "contender": contender})
            return {"effect_index": len(effects), "contender": contender}

    def contender(name: str) -> None:
        barrier.wait(timeout=5)
        try:
            result = anti_bypass.execute(action, context=runtime_context, executor=lambda: material_effect(name))
            record = {"contender": name, "outcome": "EXECUTED", "receipt_status": result.receipt_status}
        except Exception as exc:
            record = {"contender": name, "outcome": "DENIED", "error": f"{type(exc).__name__}:{exc}"}
        with results_lock:
            results.append(record)

    threads = [threading.Thread(target=contender, args=(f"contender-{i}",), daemon=True) for i in (1, 2)]
    for thread in threads:
        thread.start()
    barrier.wait(timeout=5)
    for thread in threads:
        thread.join(timeout=5)
    after = len(effects)
    executed = [r for r in results if r["outcome"] == "EXECUTED"]
    denied = [r for r in results if r["outcome"] == "DENIED"]
    verified = (
        all(not t.is_alive() for t in threads)
        and len(executed) == 1 and len(denied) == 1 and after - before == 1
        and "runtime_invalid_expired_or_replayed_receipt" in denied[0].get("error", "")
    )
    return _evidence("CONCURRENT_RECEIPT_CONFLICT", before, after, {
        "participant_count": 2,
        "synchronization": "threading.Barrier simultaneous release",
        "atomic_boundary": "ActionReceiptLedger.consume_once lock",
        "results": sorted(results, key=lambda item: item["contender"]),
        "executed_count": len(executed),
        "denied_count": len(denied),
        "semantic_sequence": "same_valid_receipt->two_concurrent_contenders->atomic_consume->one_effect->one_denial",
    }, verified)


def _build_governed_timeout_context(ctx: dict[str, Any], effects: list[dict[str, Any]]):
    action = _issue_action(ctx, digest="d2-timeout-double-execution")
    authority_id = "auth-d2-timeout"
    _register_grant(ctx, authority_id)
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
        capability_version="v1", endpoint="qualification://phase-d2-timeout",
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


def _scenario_timeout_double_execution(ctx: dict[str, Any], effects: list[dict[str, Any]]) -> SemanticScenarioEvidence:
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
    return _evidence("TIMEOUT_DOUBLE_EXECUTION", before, after, {
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
    ctx = _base_context()
    effects: list[dict[str, Any]] = []
    scenarios = [
        _scenario_revoked_authority(ctx, effects),
        _scenario_concurrent_receipt(ctx, effects),
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
    evidence["qualification_receipt"] = _digest(evidence)
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
