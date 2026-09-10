from dataclasses import dataclass
from threading import RLock
from typing import Callable, Dict, FrozenSet, Tuple
import hashlib
import time

from recursive_runtime.contracts.model import JournalRecord


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
    estimated_incremental_cost_usd: float = 0.0
    requires_paid_upgrade: bool = False


@dataclass(frozen=True)
class ActivationLease:
    lease_id: str
    environment: str
    allowed_targets: FrozenSet[str]
    allowed_capabilities: FrozenSet[str]
    founder_approval_ref: str = ""
    active: bool = False
    max_effects: int = 1
    expires_at_unix: float = 0.0


@dataclass(frozen=True)
class ProductionAuthorizationPolicy:
    policy_id: str
    allowed_ocs_ids: FrozenSet[str]
    allowed_target_prefixes: FrozenSet[str]
    allowed_capabilities: FrozenSet[str]
    founder_approval_ref: str = ""
    zero_unauthorized_spend: bool = True
    allow_github_merge: bool = False
    active: bool = False


@dataclass(frozen=True)
class VerifiedCostDecision:
    request_id: str
    target: str
    capability: str
    incremental_cost_usd: float
    paid_upgrade_required: bool
    source_ref: str
    valid_until_unix: float


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


class _BoundProviderAdapter:
    environment = "PRODUCTION"
    provider = "UNBOUND"
    TARGET_PREFIX = ""
    ALLOWED_CAPABILITIES: FrozenSet[str] = frozenset()

    def __init__(self, executor: Callable[[EffectRequest], str]):
        self.executor = executor
        self.calls = []

    def execute(self, request: EffectRequest):
        if not request.target.startswith(self.TARGET_PREFIX):
            raise RuntimeError(f"{self.provider}_TARGET_FORBIDDEN")
        if request.capability not in self.ALLOWED_CAPABILITIES:
            raise RuntimeError(f"{self.provider}_CAPABILITY_FORBIDDEN")
        self.calls.append(request)
        return self.executor(request)


class GitHubProductionAdapter(_BoundProviderAdapter):
    provider = "GITHUB"
    TARGET_PREFIX = "github:"
    ALLOWED_CAPABILITIES = frozenset({
        "GITHUB_CREATE_BRANCH",
        "GITHUB_CREATE_OR_UPDATE_FILE",
        "GITHUB_OPEN_PR",
        "GITHUB_UPDATE_PR",
        "GITHUB_MERGE_PR",
    })


class RenderProductionAdapter(_BoundProviderAdapter):
    provider = "RENDER"
    TARGET_PREFIX = "render:"
    ALLOWED_CAPABILITIES = frozenset({
        "RENDER_TRIGGER_DEPLOY",
    })


class ProductionEffectGateway:
    def __init__(
        self,
        states,
        trace,
        ocs_enforcer,
        adapter,
        activation_lease=None,
        production_policy=None,
        approval_verifier=None,
        cost_preflight=None,
        clock=None,
        effect_journal=None,
        provider_reconciler=None,
    ):
        self.states = states
        self.trace = trace
        self.ocs_enforcer = ocs_enforcer
        self.adapter = adapter
        self.activation_lease = activation_lease
        self.production_policy = production_policy
        self.approval_verifier = approval_verifier
        self.cost_preflight = cost_preflight
        self.clock = clock or time.time
        self.effect_journal = effect_journal
        self.provider_reconciler = provider_reconciler
        self._lock = RLock()
        self._receipts: Dict[str, EffectReceipt] = {}
        self._fingerprints: Dict[str, tuple] = {}
        self._lease_effect_counts: Dict[str, int] = {}

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
            request.estimated_incremental_cost_usd,
            request.requires_paid_upgrade,
        )

    @classmethod
    def _fingerprint_hash(cls, request: EffectRequest):
        return hashlib.sha256(repr(cls._fingerprint(request)).encode("utf-8")).hexdigest()

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

    def _journal_rows(self):
        return self.effect_journal.all() if self.effect_journal is not None else ()

    def _durable_effect_count(self, lease_id: str) -> int:
        count = 0
        for row in self._journal_rows():
            if row["kind"] != "PRODUCTION_EFFECT_COMMIT":
                continue
            payload = dict(row["payload"])
            if payload.get("lease_id") == lease_id:
                count += 1
        return count

    def _validate_lease(self, request: EffectRequest):
        lease = self.activation_lease
        if lease is None or not lease.active:
            raise RuntimeError("PRODUCTION_ACTIVATION_REQUIRED")
        if lease.environment != "PRODUCTION":
            raise RuntimeError("PRODUCTION_LEASE_ENVIRONMENT_MISMATCH")
        if not lease.founder_approval_ref:
            raise RuntimeError("FOUNDER_APPROVAL_REF_REQUIRED")
        if lease.max_effects <= 0:
            raise RuntimeError("PRODUCTION_LEASE_EFFECT_LIMIT_INVALID")
        if lease.expires_at_unix <= self.clock():
            raise RuntimeError("PRODUCTION_LEASE_EXPIRED")
        if request.target not in lease.allowed_targets:
            raise RuntimeError("PRODUCTION_TARGET_NOT_ALLOWED")
        if request.capability not in lease.allowed_capabilities:
            raise RuntimeError("PRODUCTION_CAPABILITY_NOT_ALLOWED")
        used = max(self._lease_effect_counts.get(lease.lease_id, 0), self._durable_effect_count(lease.lease_id))
        if used >= lease.max_effects:
            raise RuntimeError("PRODUCTION_LEASE_EFFECT_LIMIT_EXHAUSTED")

    def _validate_production_policy(self, actor, request: EffectRequest):
        policy = self.production_policy
        lease = self.activation_lease
        if policy is None or not policy.active:
            raise RuntimeError("PRODUCTION_POLICY_NOT_ACTIVE")
        if not policy.founder_approval_ref:
            raise RuntimeError("PRODUCTION_POLICY_FOUNDER_APPROVAL_REQUIRED")
        if lease.founder_approval_ref != policy.founder_approval_ref:
            raise RuntimeError("FOUNDER_APPROVAL_REF_MISMATCH")
        if self.approval_verifier is None:
            raise RuntimeError("FOUNDER_APPROVAL_VERIFIER_NOT_BOUND")
        if not self.approval_verifier(policy, lease, actor, request):
            raise RuntimeError("FOUNDER_APPROVAL_NOT_VERIFIED")
        if actor.identity_id not in policy.allowed_ocs_ids:
            raise RuntimeError("PRODUCTION_OCS_NOT_ALLOWED")
        if request.capability not in policy.allowed_capabilities:
            raise RuntimeError("PRODUCTION_POLICY_CAPABILITY_NOT_ALLOWED")
        if not any(request.target.startswith(prefix) for prefix in policy.allowed_target_prefixes):
            raise RuntimeError("PRODUCTION_POLICY_TARGET_NOT_ALLOWED")
        if request.capability == "GITHUB_MERGE_PR" and not policy.allow_github_merge:
            raise RuntimeError("GITHUB_MERGE_REQUIRES_EXPLICIT_POLICY")
        if policy.zero_unauthorized_spend:
            if request.estimated_incremental_cost_usd != 0:
                raise RuntimeError("ZERO_SPEND_POLICY_VIOLATION")
            if request.requires_paid_upgrade:
                raise RuntimeError("PAID_UPGRADE_FORBIDDEN")
            if self.cost_preflight is None:
                raise RuntimeError("COST_PREFLIGHT_NOT_BOUND")
            decision = self.cost_preflight(request)
            if not isinstance(decision, VerifiedCostDecision) or not decision.source_ref:
                raise RuntimeError("COST_PREFLIGHT_UNVERIFIED")
            if decision.request_id != request.request_id or decision.target != request.target or decision.capability != request.capability:
                raise RuntimeError("COST_PREFLIGHT_SCOPE_MISMATCH")
            if decision.valid_until_unix <= self.clock():
                raise RuntimeError("COST_PREFLIGHT_EXPIRED")
            if decision.incremental_cost_usd != 0:
                raise RuntimeError("ZERO_SPEND_POLICY_VIOLATION")
            if decision.paid_upgrade_required:
                raise RuntimeError("PAID_UPGRADE_FORBIDDEN")

    def _find_durable(self, request_id: str):
        intent = commit = None
        for row in self._journal_rows():
            payload = dict(row["payload"])
            if payload.get("request_id") != request_id:
                continue
            if row["kind"] == "PRODUCTION_EFFECT_INTENT":
                intent = row
            elif row["kind"] == "PRODUCTION_EFFECT_COMMIT":
                commit = row
        return intent, commit

    def _validate_durable_row(self, row, request: EffectRequest):
        payload = dict(row["payload"])
        if payload.get("fingerprint") != self._fingerprint_hash(request):
            raise RuntimeError("DURABLE_EFFECT_REQUEST_CONFLICT")
        return payload

    def _receipt_from_commit(self, request: EffectRequest, commit):
        payload = self._validate_durable_row(commit, request)
        return EffectReceipt(
            request_id=request.request_id,
            actor_id=request.actor_id,
            target=request.target,
            capability=request.capability,
            payload_ref=request.payload_ref,
            adapter_environment="PRODUCTION",
            status="COMMITTED",
            result_ref=payload["result_ref"],
        )

    def _persist_intent(self, actor, request: EffectRequest):
        if self.effect_journal is None:
            raise RuntimeError("EFFECT_JOURNAL_NOT_BOUND")
        lease = self.activation_lease
        self.effect_journal.put(JournalRecord(
            journal_id=f"effect-intent:{request.request_id}",
            kind="PRODUCTION_EFFECT_INTENT",
            actor_id=actor.actor_id,
            trace_id=actor.trace_id,
            generation=actor.generation,
            fencing_epoch=actor.fencing_epoch,
            status="INTENT_PERSISTED",
            payload=(("request_id",request.request_id),("fingerprint",self._fingerprint_hash(request)),("target",request.target),("capability",request.capability),("payload_ref",request.payload_ref),("lease_id",lease.lease_id)),
        ))

    def _persist_commit(self, actor, request: EffectRequest, result_ref: str):
        lease = self.activation_lease
        self.effect_journal.put(JournalRecord(
            journal_id=f"effect-commit:{request.request_id}",
            kind="PRODUCTION_EFFECT_COMMIT",
            actor_id=actor.actor_id,
            trace_id=actor.trace_id,
            generation=actor.generation,
            fencing_epoch=actor.fencing_epoch,
            status="COMMITTED",
            payload=(("request_id",request.request_id),("fingerprint",self._fingerprint_hash(request)),("target",request.target),("capability",request.capability),("payload_ref",request.payload_ref),("lease_id",lease.lease_id),("result_ref",result_ref)),
        ))

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
                if self.effect_journal is None:
                    raise RuntimeError("EFFECT_JOURNAL_NOT_BOUND")
                intent, commit = self._find_durable(request.request_id)
                if commit is not None:
                    receipt = self._receipt_from_commit(request, commit)
                    self._fingerprints[request.request_id] = fp
                    self._receipts[request.request_id] = receipt
                    return receipt
                if intent is not None:
                    self._validate_durable_row(intent, request)
                    if self.provider_reconciler is None:
                        raise RuntimeError("EFFECT_OUTCOME_UNKNOWN_HOLD")
                    result_ref = self.provider_reconciler(request)
                    if not result_ref:
                        raise RuntimeError("EFFECT_OUTCOME_UNKNOWN_HOLD")
                    self._persist_commit(actor, request, result_ref)
                    receipt = self._receipt_from_commit(request, self._find_durable(request.request_id)[1])
                    self._fingerprints[request.request_id] = fp
                    self._receipts[request.request_id] = receipt
                    self._lease_effect_counts[self.activation_lease.lease_id] = self._durable_effect_count(self.activation_lease.lease_id)
                    return receipt
                self._validate_lease(request)
                self._validate_production_policy(actor, request)
                self._persist_intent(actor, request)
            elif env != "SANDBOX":
                raise RuntimeError("UNKNOWN_EFFECT_ADAPTER_ENVIRONMENT")

            result_ref = self.adapter.execute(request)
            if env == "PRODUCTION":
                self._persist_commit(actor, request, result_ref)
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
            if env == "PRODUCTION":
                lease_id = self.activation_lease.lease_id
                self._lease_effect_counts[lease_id] = self._durable_effect_count(lease_id)
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
