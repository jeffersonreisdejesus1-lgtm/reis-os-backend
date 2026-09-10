from dataclasses import dataclass
from threading import RLock
from typing import Dict, FrozenSet, Tuple


@dataclass(frozen=True)
class EffectRequest:
    request_id: str
    actor_id: str
    target: str
    capability: str
    payload_ref: str
    authority_ref: str
    mission_binding: str
    generation: int
    fencing_epoch: int


@dataclass(frozen=True)
class ActivationLease:
    lease_id: str
    environment: str
    allowed_targets: FrozenSet[str]
    allowed_capabilities: FrozenSet[str]
    founder_approval_ref: str = ""
    active: bool = False


@dataclass(frozen=True)
class EffectReceipt:
    request_id: str
    actor_id: str
    target: str
    capability: str
    payload_ref: str
    adapter_environment: str
    status: str
    result_ref: str


class SandboxEffectAdapter:
    environment = "SANDBOX"

    def __init__(self):
        self.calls = []

    def execute(self, request: EffectRequest):
        self.calls.append(request)
        return f"sandbox:{request.request_id}:{request.payload_ref}"


class ProductionEffectAdapter:
    environment = "PRODUCTION"

    def execute(self, request: EffectRequest):
        raise RuntimeError("REAL_PROVIDER_ADAPTER_NOT_BOUND")


class ProductionEffectGateway:
    def __init__(self, states, trace, ocs_enforcer, adapter, activation_lease=None):
        self.states = states
        self.trace = trace
        self.ocs_enforcer = ocs_enforcer
        self.adapter = adapter
        self.activation_lease = activation_lease
        self._lock = RLock()
        self._receipts: Dict[str, EffectReceipt] = {}
        self._fingerprints: Dict[str, tuple] = {}

    @staticmethod
    def _fingerprint(request: EffectRequest):
        return (
            request.actor_id,
            request.target,
            request.capability,
            request.payload_ref,
            request.authority_ref,
            request.mission_binding,
            request.generation,
            request.fencing_epoch,
        )

    def _validate_common(self, request: EffectRequest):
        actor = self.states.get(request.actor_id)
        self.states.validate_current(actor.actor_id, request.generation, request.fencing_epoch)
        self.ocs_enforcer.binding_for_actor(actor)
        if actor.authority.authority_ref != request.authority_ref:
            raise RuntimeError("EFFECT_AUTHORITY_MISMATCH")
        if actor.mission_binding != request.mission_binding:
            raise RuntimeError("EFFECT_MISSION_MISMATCH")
        if request.capability not in actor.capability.capabilities:
            raise RuntimeError("EFFECT_CAPABILITY_NOT_BOUND")
        return actor

    def _validate_lease(self, request: EffectRequest):
        lease = self.activation_lease
        if lease is None or not lease.active:
            raise RuntimeError("PRODUCTION_ACTIVATION_REQUIRED")
        if lease.environment != "PRODUCTION":
            raise RuntimeError("PRODUCTION_LEASE_ENVIRONMENT_MISMATCH")
        if not lease.founder_approval_ref:
            raise RuntimeError("FOUNDER_APPROVAL_REF_REQUIRED")
        if request.target not in lease.allowed_targets:
            raise RuntimeError("PRODUCTION_TARGET_NOT_ALLOWED")
        if request.capability not in lease.allowed_capabilities:
            raise RuntimeError("PRODUCTION_CAPABILITY_NOT_ALLOWED")

    def execute(self, request: EffectRequest):
        fp = self._fingerprint(request)
        with self._lock:
            existing = self._receipts.get(request.request_id)
            if existing is not None:
                if self._fingerprints[request.request_id] != fp:
                    raise RuntimeError("EFFECT_REQUEST_ID_CONFLICT")
                return existing

            actor = self._validate_common(request)
            env = getattr(self.adapter, "environment", None)
            if env == "PRODUCTION":
                self._validate_lease(request)
                ok, detail = self.ocs_enforcer.authorize_effect(actor, "PRODUCTION_EFFECT")
                if not ok:
                    raise RuntimeError(detail)
            elif env != "SANDBOX":
                raise RuntimeError("UNKNOWN_EFFECT_ADAPTER_ENVIRONMENT")

            result_ref = self.adapter.execute(request)
            receipt = EffectReceipt(
                request_id=request.request_id,
                actor_id=request.actor_id,
                target=request.target,
                capability=request.capability,
                payload_ref=request.payload_ref,
                adapter_environment=env,
                status="SIMULATED" if env == "SANDBOX" else "COMMITTED",
                result_ref=result_ref,
            )
            self._fingerprints[request.request_id] = fp
            self._receipts[request.request_id] = receipt
            self.trace.emit(
                "PRODUCTION_EFFECT_GATEWAY",
                actor,
                f"request={request.request_id};target={request.target};capability={request.capability};environment={env};status={receipt.status};result={result_ref}",
                receipt_id=f"effect:{request.request_id}",
            )
            return receipt

    def receipts(self) -> Tuple[EffectReceipt, ...]:
        with self._lock:
            return tuple(self._receipts.values())
