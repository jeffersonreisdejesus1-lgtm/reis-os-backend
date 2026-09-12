from __future__ import annotations

from dataclasses import replace
from threading import Barrier, Thread
from types import SimpleNamespace

from app.cognitive_validation.action_receipt import (
    ActionCognitiveReceiptIssuer,
    ActionReceiptLedger,
)
from app.cognitive_validation.adapter_fabric import (
    AdapterHealth,
    AdapterInvocationContext,
    AdapterRecord,
    InstitutionalAdapterFabric,
)
from app.cognitive_validation.adversarial_failure_bypass import (
    AdversarialFailureBypassQualifier,
)
from app.cognitive_validation.authority_aware_discovery import (
    AuthorityAwareCapabilityDiscovery,
    AuthorityGrant,
    InstitutionalAuthorityRegistry,
)
from app.cognitive_validation.bootstrap_binding import BootstrapCognitiveBinding
from app.cognitive_validation.capability_fabric import (
    CapabilityHealth,
    CapabilityRecord,
    InstitutionalCapabilityFabric,
)
from app.cognitive_validation.contracts import (
    CognitiveValidationContract,
    enforce_cognitive_contract,
)
from app.cognitive_validation.mission_receipt import MissionCognitiveReceiptIssuer
from app.cognitive_validation.observation_evidence_state import (
    EffectObservation,
    InstitutionalStateStore,
    ObservationEvidenceStateUpdater,
)
from app.cognitive_validation.runtime_adversarial_evidence import (
    RuntimeAdversarialEvidenceLedger,
)
from app.cognitive_validation.runtime_anti_bypass import (
    RuntimeAntiBypassGateway,
    RuntimeExecutionContext,
)
from app.cognitive_validation.universal_entrypoint import (
    CognitiveMissionContext,
    UniversalCognitiveEntrypoint,
)


class ExplodingBrain:
    version = "coi15/runtime-unavailable"

    def evaluate(self, context: CognitiveMissionContext) -> float:
        del context
        raise RuntimeError("brain unavailable")


def _binding() -> BootstrapCognitiveBinding:
    return BootstrapCognitiveBinding(
        binding_id="binding:coi15-hold-002",
        mission_id="mission-hold-002",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-hold-002",
        generation=15,
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        brain_path="AB0-AB13/canonical",
        authority_ref="authority:hold-002",
        state_namespace="state:hold-002",
        memory_namespace="memory:hold-002",
    )


def _mission_issuer(now: float = 100.0) -> MissionCognitiveReceiptIssuer:
    return MissionCognitiveReceiptIssuer(
        signing_secret=b"coi15-mission-secret",
        clock=lambda: now,
        nonce_factory=lambda: "coi15-mission-nonce",
    )


def _action_system(*, now: float = 101.0, ledger: ActionReceiptLedger | None = None):
    mi = _mission_issuer(100.0)
    ai = ActionCognitiveReceiptIssuer(
        signing_secret=b"coi15-action-secret",
        mission_issuer=mi,
        ledger=ledger,
        clock=lambda: now,
        nonce_factory=lambda: "coi15-action-nonce",
        ttl_seconds=60,
    )
    mission = mi.issue(
        _binding(),
        intent="exercise adversarial runtime controls",
        state_revision="state-r15",
        state_hash="state-hash-15",
        cognition_cycle_id="cycle-hold-002",
    )
    action = ai.issue(
        mission,
        plan_hash="plan-hold-002",
        action_digest="action-hold-002",
        capability_id="github",
        capability_version="v1",
        adapter_version="adapter-v1",
        authority_requirements=("repo:write",),
        state_hash="state-hash-15",
        policy_version="policy-v1",
    )
    context = RuntimeExecutionContext(
        mission_id="mission-hold-002",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-hold-002",
        generation=15,
        capability_id="github",
        capability_version="v1",
        adapter_version="adapter-v1",
        action_digest="action-hold-002",
        state_hash="state-hash-15",
        policy_version="policy-v1",
    )
    return ai, action, context


def _capability_record(**changes) -> CapabilityRecord:
    values = dict(
        capability_id="github",
        capability_version="v1",
        adapter_id="github-adapter",
        adapter_version="adapter-v1",
        endpoint="github://api",
        schema_version="schema-v1",
        health=CapabilityHealth.HEALTHY,
        authorized_missions=("mission-hold-002",),
    )
    values.update(changes)
    return CapabilityRecord(**values)


def _authority_system():
    ai, action, _ = _action_system()
    fabric = InstitutionalCapabilityFabric([_capability_record()])
    registry = InstitutionalAuthorityRegistry()
    registry.register(
        AuthorityGrant(
            authority_id="auth-hold-002",
            mission_id="mission-hold-002",
            ocs_id="NOESIS",
            capability_id="github",
            adapter_version="adapter-v1",
            operation_class="CLASS_3",
            policy_version="policy-v1",
            authority_requirements=("repo:write",),
            valid_from=90.0,
            valid_until=200.0,
        )
    )
    discovery = AuthorityAwareCapabilityDiscovery(
        capability_fabric=fabric,
        authority_registry=registry,
        action_issuer=ai,
        signing_secret=b"coi15-authority-secret",
        clock=lambda: 101.0,
        nonce_factory=lambda: "coi15-authority-nonce",
    )
    return discovery, registry, action


def _adapter_attack_unavailable() -> None:
    fabric = InstitutionalCapabilityFabric([_capability_record()])
    discovery = fabric.discover(
        "github", mission_id="mission-hold-002", required_schema_version="schema-v1"
    )
    adapters = InstitutionalAdapterFabric()
    adapters.register(
        AdapterRecord(
            adapter_id="github-adapter",
            adapter_version="adapter-v1",
            capability_id="github",
            capability_version="v1",
            endpoint="github://api",
            input_schema_version="schema-v1",
            output_schema_version="schema-v1",
            health=AdapterHealth.UNAVAILABLE,
        ),
        lambda payload: {"ok": True, **payload},
    )
    adapters.execute(
        discovery,
        AdapterInvocationContext(
            mission_id="mission-hold-002",
            action_receipt_id="acr-runtime",
            authority_receipt_id="authority-runtime",
            capability_discovery_receipt=discovery.discovery_receipt,
            input_schema_version="schema-v1",
            expected_output_schema_version="schema-v1",
        ),
        {},
    )


def _observation(status: str = "EXECUTED_CONFIRMED", receipt: str = "exec-1", effect=None):
    if effect is None:
        effect = {"commit": "abc123"}
    execution = SimpleNamespace(
        mission_id="mission-hold-002",
        capability_id="github",
        ocs_id="SOFIA",
        governed_execution_receipt=receipt,
        execution_status=status,
        adapter_execution_receipt=SimpleNamespace(execution_receipt="adapter-exec-1"),
    )
    observation = EffectObservation(
        mission_id="mission-hold-002",
        capability_id="github",
        ocs_id="SOFIA",
        governed_execution_receipt=receipt,
        execution_status=status,
        observed_effect=effect,
    )
    return execution, observation


def test_hold_002_all_required_attack_classes_derive_probe_fields_from_runtime() -> None:
    ledger = RuntimeAdversarialEvidenceLedger()
    probes = []
    no_effect = lambda: 0

    # COI5 direct bypass / receipt integrity / expiry / context / replay.
    ai, action, context = _action_system(ledger=ActionReceiptLedger())
    gateway = RuntimeAntiBypassGateway(action_issuer=ai)
    calls: list[str] = []
    probes.append(ledger.execute_probe(
        probe_id="runtime-direct-bypass", attack_class="DIRECT_SOFTWARE_BYPASS",
        attempted_action="execute without action receipt",
        attack=lambda: gateway.execute(None, context=context, executor=lambda: calls.append("effect")),
        effect_counter=lambda: len(calls),
    ))
    probes.append(ledger.execute_probe(
        probe_id="runtime-fake-receipt", attack_class="FAKE_RECEIPT",
        attempted_action="execute with tampered signature",
        attack=lambda: gateway.execute(replace(action, signature="0" * 64), context=context, executor=lambda: calls.append("effect")),
        effect_counter=lambda: len(calls),
    ))

    issuing_ai, expiring_action, expiring_context = _action_system(now=101.0)
    expired_ai = ActionCognitiveReceiptIssuer(
        signing_secret=b"coi15-action-secret", mission_issuer=_mission_issuer(100.0),
        clock=lambda: 1000.0, ttl_seconds=60,
    )
    expired_gateway = RuntimeAntiBypassGateway(action_issuer=expired_ai)
    probes.append(ledger.execute_probe(
        probe_id="runtime-expired-receipt", attack_class="EXPIRED_RECEIPT",
        attempted_action="execute expired action receipt",
        attack=lambda: expired_gateway.execute(expiring_action, context=expiring_context, executor=lambda: calls.append("expired")),
        effect_counter=lambda: len(calls),
    ))
    probes.append(ledger.execute_probe(
        probe_id="runtime-wrong-context", attack_class="WRONG_CONTEXT_RECEIPT",
        attempted_action="execute receipt in wrong mission context",
        attack=lambda: gateway.execute(action, context=replace(context, mission_id="other-mission"), executor=lambda: calls.append("wrong")),
        effect_counter=lambda: len(calls),
    ))

    replay_ai, replay_action, replay_context = _action_system(ledger=ActionReceiptLedger())
    replay_gateway = RuntimeAntiBypassGateway(action_issuer=replay_ai)
    replay_calls: list[str] = []
    replay_gateway.execute(replay_action, context=replay_context, executor=lambda: replay_calls.append("first"))
    probes.append(ledger.execute_probe(
        probe_id="runtime-replay", attack_class="REPLAY",
        attempted_action="reuse consumed action receipt",
        attack=lambda: replay_gateway.execute(replay_action, context=replay_context, executor=lambda: replay_calls.append("duplicate")),
        effect_counter=lambda: max(0, len(replay_calls) - 1),
    ))

    # COI8 authority controls.
    authority, registry, authority_action = _authority_system()
    probes.append(ledger.execute_probe(
        probe_id="runtime-no-authority", attack_class="CAPABILITY_WITHOUT_AUTHORITY",
        attempted_action="discover capability with absent authority grant",
        attack=lambda: authority.discover(
            capability_id="github", required_schema_version="schema-v1",
            action_receipt=authority_action, authority_id="missing", operation_class="CLASS_3"
        ), effect_counter=no_effect,
    ))
    registry.revoke("auth-hold-002")
    probes.append(ledger.execute_probe(
        probe_id="runtime-revoked-authority", attack_class="REVOKED_AUTHORITY",
        attempted_action="execute discovery after authority revocation",
        attack=lambda: authority.discover(
            capability_id="github", required_schema_version="schema-v1",
            action_receipt=authority_action, authority_id="auth-hold-002", operation_class="CLASS_3"
        ), effect_counter=no_effect,
    ))

    # COI1 fail-closed brain path.
    mission_context = CognitiveMissionContext(
        mission_id="mission-hold-002", ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-hold-002", generation=15,
        intent="adversarial brain availability probe", state_revision="state-r15",
    )
    probes.append(ledger.execute_probe(
        probe_id="runtime-brain-unavailable", attack_class="BRAIN_UNAVAILABLE",
        attempted_action="enter cognition while brain backend is unavailable",
        attack=lambda: UniversalCognitiveEntrypoint(ExplodingBrain()).enter(mission_context),
        effect_counter=no_effect,
    ))

    # COI6/7 capability and adapter controls.
    probes.append(ledger.execute_probe(
        probe_id="runtime-adapter-unavailable", attack_class="ADAPTER_UNAVAILABLE",
        attempted_action="invoke unavailable registered adapter",
        attack=_adapter_attack_unavailable, effect_counter=no_effect,
    ))
    capability_fabric = InstitutionalCapabilityFabric([_capability_record()])
    probes.append(ledger.execute_probe(
        probe_id="runtime-hallucinated-capability", attack_class="HALLUCINATED_CAPABILITY",
        attempted_action="discover capability absent from institutional registry",
        attack=lambda: capability_fabric.discover(
            "hallucinated", mission_id="mission-hold-002", required_schema_version="schema-v1"
        ), effect_counter=no_effect,
    ))
    probes.append(ledger.execute_probe(
        probe_id="runtime-schema-mismatch", attack_class="SCHEMA_MISMATCH",
        attempted_action="discover capability with incompatible schema",
        attack=lambda: capability_fabric.discover(
            "github", mission_id="mission-hold-002", required_schema_version="schema-v2"
        ), effect_counter=no_effect,
    ))

    # Stale state is rejected by the exact COI5 runtime context binding.
    stale_ai, stale_action, stale_context = _action_system(ledger=ActionReceiptLedger())
    stale_gateway = RuntimeAntiBypassGateway(action_issuer=stale_ai)
    stale_calls: list[str] = []
    probes.append(ledger.execute_probe(
        probe_id="runtime-stale-state", attack_class="STALE_STATE",
        attempted_action="execute action against changed state hash",
        attack=lambda: stale_gateway.execute(
            stale_action, context=replace(stale_context, state_hash="state-hash-new"),
            executor=lambda: stale_calls.append("effect")
        ), effect_counter=lambda: len(stale_calls),
    ))

    # COI11 evidence/state qualification.
    store = InstitutionalStateStore()
    updater = ObservationEvidenceStateUpdater(state_store=store)
    success_exec, no_evidence = _observation(effect={})
    probes.append(ledger.execute_probe(
        probe_id="runtime-success-without-evidence", attack_class="SUCCESS_WITHOUT_EVIDENCE",
        attempted_action="qualify successful execution without observed effect",
        attack=lambda: updater.qualify_and_update(
            execution=success_exec, observation=no_evidence, state_delta={"x": 1}
        ), effect_counter=no_effect,
    ))
    unknown_exec, unknown_obs = _observation(status="EXECUTION_UNKNOWN", receipt="exec-unknown")
    probes.append(ledger.execute_probe(
        probe_id="runtime-execution-unknown", attack_class="EXECUTION_UNKNOWN",
        attempted_action="commit state while execution outcome is unknown",
        attack=lambda: updater.qualify_and_update(
            execution=unknown_exec, observation=unknown_obs, state_delta={"x": 2}
        ), effect_counter=no_effect,
    ))
    partial_exec, partial_obs = _observation(status="EXECUTED_PARTIAL", receipt="exec-partial")
    probes.append(ledger.execute_probe(
        probe_id="runtime-partial-effect", attack_class="PARTIAL_EFFECT",
        attempted_action="blindly qualify partial effect as committed success",
        attack=lambda: updater.qualify_and_update(
            execution=partial_exec, observation=partial_obs, state_delta={"x": 3}
        ), effect_counter=no_effect,
    ))

    # COI4 atomic ledger resolves concurrent consumers to one material invocation.
    concurrent_ai, concurrent_action, concurrent_context = _action_system(ledger=ActionReceiptLedger())
    concurrent_gateway = RuntimeAntiBypassGateway(action_issuer=concurrent_ai)
    concurrent_calls: list[str] = []
    concurrent_errors: list[Exception] = []
    barrier = Barrier(2)

    def concurrent_attempt() -> None:
        try:
            barrier.wait()
            concurrent_gateway.execute(
                concurrent_action, context=concurrent_context,
                executor=lambda: concurrent_calls.append("effect"),
            )
        except Exception as exc:
            concurrent_errors.append(exc)

    def launch_conflict() -> None:
        threads = [Thread(target=concurrent_attempt), Thread(target=concurrent_attempt)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if len(concurrent_calls) != 1 or len(concurrent_errors) != 1:
            raise AssertionError("concurrent_receipt_conflict_not_contained")
        raise RuntimeError("concurrent_receipt_conflict_contained")

    probes.append(ledger.execute_probe(
        probe_id="runtime-concurrent-conflict", attack_class="CONCURRENT_RECEIPT_CONFLICT",
        attempted_action="race two executions using one action receipt",
        attack=launch_conflict,
        effect_counter=lambda: max(0, len(concurrent_calls) - 1),
    ))

    # A timeout after first invocation consumes the receipt before the effect; blind
    # retry cannot produce a second material invocation.
    timeout_ai, timeout_action, timeout_context = _action_system(ledger=ActionReceiptLedger())
    timeout_gateway = RuntimeAntiBypassGateway(action_issuer=timeout_ai)
    timeout_calls: list[str] = []

    def timed_out_executor() -> None:
        timeout_calls.append("first")
        raise TimeoutError("outcome unknown after invocation")

    try:
        timeout_gateway.execute(timeout_action, context=timeout_context, executor=timed_out_executor)
    except TimeoutError:
        pass
    probes.append(ledger.execute_probe(
        probe_id="runtime-timeout-double-exec", attack_class="TIMEOUT_DOUBLE_EXECUTION",
        attempted_action="blind retry after timeout with unknown execution outcome",
        attack=lambda: timeout_gateway.execute(
            timeout_action, context=timeout_context,
            executor=lambda: timeout_calls.append("duplicate")
        ),
        effect_counter=lambda: max(0, len(timeout_calls) - 1),
    ))

    # AB0 constitutional contract is now executable as a fail-closed guard.
    probes.append(ledger.execute_probe(
        probe_id="runtime-constitutional-self-mod", attack_class="CONSTITUTIONAL_SELF_MODIFICATION",
        attempted_action="allow adaptation to rewrite constitutional constraints",
        attack=lambda: enforce_cognitive_contract(
            CognitiveValidationContract(adaptation_may_rewrite_constitution=True)
        ), effect_counter=no_effect,
    ))

    # Falsified evidence is rejected by execution/evidence correlation before state mutation.
    false_exec, false_obs = _observation(receipt="exec-real")
    false_obs = replace(false_obs, governed_execution_receipt="exec-forged")
    probes.append(ledger.execute_probe(
        probe_id="runtime-falsified-evidence", attack_class="FALSIFIED_EVIDENCE",
        attempted_action="commit observation bound to forged execution receipt",
        attack=lambda: ObservationEvidenceStateUpdater(
            state_store=InstitutionalStateStore()
        ).qualify_and_update(
            execution=false_exec, observation=false_obs, state_delta={"x": 4}
        ), effect_counter=no_effect,
    ))

    result = AdversarialFailureBypassQualifier().qualify(probes)
    assert set(result.covered_attack_classes) == AdversarialFailureBypassQualifier.REQUIRED_ATTACK_CLASSES
    assert len(ledger.events) == 19
    assert all(event.exception_type for event in ledger.events)
    assert all(event.evidence_ref.startswith("runtime-evidence:") for event in ledger.events)
    assert all(not event.effect_observed for event in ledger.events)
    assert result.qualification_receipt
