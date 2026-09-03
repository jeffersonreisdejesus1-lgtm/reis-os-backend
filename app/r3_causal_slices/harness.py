from __future__ import annotations

from dataclasses import dataclass, field

from app.profile_bindings.profiles import OCSProfile, PROFILES
from app.universal_kernel.state_trace import StateCore


@dataclass(frozen=True)
class CausalEvent:
    stage: str
    outcome: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CausalReceipt:
    slice_id: str
    trace_id: str
    outcome: str
    mutation_count: int
    effector_attempt: bool
    state_delta: str
    events: tuple[CausalEvent, ...]
    readback_oracle: str
    recovery_oracle: str | None = None

    def has_stage(self, stage: str) -> bool:
        return any(event.stage == stage for event in self.events)

    def event(self, stage: str) -> CausalEvent:
        return next(event for event in self.events if event.stage == stage)


class CausalRecorder:
    def __init__(self, slice_id: str, trace_id: str) -> None:
        self.slice_id = slice_id
        self.trace_id = trace_id
        self._events: list[CausalEvent] = []

    def append(self, stage: str, outcome: str, **details: object) -> None:
        self._events.append(CausalEvent(stage, outcome, details))

    @property
    def events(self) -> tuple[CausalEvent, ...]:
        return tuple(self._events)

    def receipt(
        self,
        *,
        outcome: str,
        mutation_count: int,
        effector_attempt: bool,
        state_delta: str,
        readback_oracle: str,
        recovery_oracle: str | None = None,
    ) -> CausalReceipt:
        self.append("CAUSAL_TRACE", "CLOSED", trace_id=self.trace_id)
        self.append("RECEIPT", outcome, slice_id=self.slice_id)
        return CausalReceipt(
            slice_id=self.slice_id,
            trace_id=self.trace_id,
            outcome=outcome,
            mutation_count=mutation_count,
            effector_attempt=effector_attempt,
            state_delta=state_delta,
            events=self.events,
            readback_oracle=readback_oracle,
            recovery_oracle=recovery_oracle,
        )


class NamespaceGuard:
    def attempt_state_write(
        self,
        *,
        profile: OCSProfile,
        requested_namespace: str,
        state: StateCore,
        recorder: CausalRecorder,
    ) -> bool:
        recorder.append("GOAL", "STATE_WRITE_REQUESTED", ocs=profile.ocs_id)
        recorder.append("COGNITIVE_PLAN", "NAMESPACE_BOUND_WRITE")
        recorder.append(
            "ACTION_PROPOSAL",
            "STATE_WRITE",
            namespace=requested_namespace,
        )
        allowed = requested_namespace.startswith(profile.state_namespace)
        recorder.append(
            "GOVERNANCE_DECISION",
            "ALLOW" if allowed else "DENY_NAMESPACE",
            bound_namespace=profile.state_namespace,
        )
        if not allowed:
            recorder.append("STATE_COMMIT_OR_NO_COMMIT", "NO_COMMIT")
            return False
        return state.current(profile.ocs_id) is not None


class EffectBoundaryGuard:
    def attempt_lateral_route(
        self,
        *,
        profile: OCSProfile,
        route: str,
        recorder: CausalRecorder,
    ) -> bool:
        recorder.append("GOAL", "MATERIAL_EFFECT_REQUESTED", ocs=profile.ocs_id)
        recorder.append("COGNITIVE_PLAN", "EFFECT_ROUTE_SELECTION")
        recorder.append("ACTION_PROPOSAL", "LATERAL_ROUTE_ATTEMPT", route=route)
        permitted = bool(profile.capability_adapters or profile.tool_permissions)
        recorder.append(
            "GOVERNANCE_DECISION",
            "ALLOW" if permitted else "DENY_ROUTE",
        )
        if not permitted:
            recorder.append("MATERIAL_EFFECT_ATTEMPT", "NOT_ATTEMPTED")
            recorder.append("STATE_COMMIT_OR_NO_COMMIT", "NO_COMMIT")
        return permitted


@dataclass(frozen=True)
class SpecialtyExecution:
    profile_id: str
    goal: str
    selected_action: str
    specialty: str
    handoff_required: bool
    events: tuple[CausalEvent, ...]


class SpecialtyGoalExecutor:
    def execute(self, *, profile_id: str, goal: str) -> SpecialtyExecution:
        profile = PROFILES[profile_id]
        recorder = CausalRecorder(
            "R3-S10",
            f"trace:r3-s10:{profile_id.lower()}",
        )
        recorder.append("GOAL", "RECEIVED", goal=goal, ocs=profile_id)
        action = profile.allowed_action_classes[0]
        recorder.append(
            "COGNITIVE_PLAN",
            "SPECIALTY_LOCAL_DECOMPOSITION",
            specialty=profile.specialty,
            selected_action=action,
        )
        handoff_required = goal not in profile.specialty
        recorder.append(
            "ACTION_PROPOSAL",
            action,
            authority_ref=profile.authority_envelope_ref,
        )
        recorder.append(
            "RECEIPT",
            "SPECIALTY_EXECUTION_OBSERVED",
            handoff_required=handoff_required,
        )
        return SpecialtyExecution(
            profile_id=profile_id,
            goal=goal,
            selected_action=action,
            specialty=profile.specialty,
            handoff_required=handoff_required,
            events=recorder.events,
        )
