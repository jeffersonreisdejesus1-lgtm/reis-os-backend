from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from .contracts import ActionProposal, HandoffPackage
from .state import InMemoryStateManager, StateSnapshot
from .trace import TraceLedger


@dataclass(frozen=True)
class IdentityContext:
    ocs_id: str
    profile_version: str
    ancestry_ref: str
    constitution_ref: str


@dataclass(frozen=True)
class ConstitutionSnapshot:
    constitution_ref: str
    policy_version: str
    inherited_prohibitions: tuple[str, ...]
    content_hash: str


class ConstitutionLoader:
    def load(
        self,
        constitution_ref: str,
        policy_version: str,
        inherited_prohibitions: tuple[str, ...],
    ) -> ConstitutionSnapshot:
        if not constitution_ref or not policy_version:
            raise RuntimeError("HOLD_CONSTITUTION_SOURCE")
        canonical = json.dumps(
            {
                "constitution_ref": constitution_ref,
                "policy_version": policy_version,
                "prohibitions": inherited_prohibitions,
            },
            sort_keys=True,
        )
        return ConstitutionSnapshot(
            constitution_ref=constitution_ref,
            policy_version=policy_version,
            inherited_prohibitions=inherited_prohibitions,
            content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
        )


@dataclass(frozen=True)
class PIActivationSet:
    activations: tuple[str, ...]
    reasons: tuple[str, ...]


class PIActivation:
    VALID_MODES = {
        "CORE_ALWAYS",
        "RISK_TRIGGERED",
        "SPECIALTY_NATIVE",
        "ON_DEMAND",
        "HANDOFF_BOUND",
        "DEFERRED",
    }

    def activate(self, requested: tuple[tuple[str, str], ...]) -> PIActivationSet:
        for _, mode in requested:
            if mode not in self.VALID_MODES:
                raise ValueError("invalid PI activation mode")
        return PIActivationSet(
            activations=tuple(name for name, _ in requested),
            reasons=tuple(mode for _, mode in requested),
        )


class CognitiveRuntimePort:
    """Proposal-only cognitive boundary. No mutable adapter is exposed here."""

    def propose(
        self,
        *,
        proposal_id: str,
        actor: str,
        ocs_id: str,
        csp_ref: str,
        goal_ref: str,
        action_type: str,
        object_ref: str,
        scope_requested: str,
        capability_ref: str,
        evidence_refs: tuple[str, ...],
        expected_effect: str,
        side_effect_class: str,
        reversibility_class: str,
        context_ref: str,
        authority_ref: str | None,
    ) -> ActionProposal:
        return ActionProposal(
            proposal_id=proposal_id,
            actor=actor,
            ocs_id=ocs_id,
            csp_ref=csp_ref,
            goal_ref=goal_ref,
            action_type=action_type,
            object_ref=object_ref,
            scope_requested=scope_requested,
            capability_ref=capability_ref,
            evidence_refs=evidence_refs,
            expected_effect=expected_effect,
            side_effect_class=side_effect_class,
            reversibility_class=reversibility_class,
            context_ref=context_ref,
            authority_ref=authority_ref,
        )


class RecoveryManager:
    def __init__(self, state: InMemoryStateManager, trace: TraceLedger) -> None:
        self._state = state
        self._trace = trace

    def restore_verified(self, checkpoint_ref: str) -> StateSnapshot:
        restored = self._state.rollback_to_verified(checkpoint_ref)
        self._trace.append(
            "recovery_receipt",
            {"checkpoint_ref": checkpoint_ref, "hash": restored.content_hash},
        )
        return restored


class HandoffRouter:
    def create_package(
        self,
        *,
        handoff_id: str,
        from_ocs: str,
        to_ocs: str,
        object_ref: str,
        context_refs: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        open_findings: tuple[str, ...],
        requested_scope: str,
        prohibited_consequences: tuple[str, ...],
        predecessor_receipt_ref: str,
    ) -> HandoffPackage:
        return HandoffPackage(
            handoff_id=handoff_id,
            from_ocs=from_ocs,
            to_ocs=to_ocs,
            object_ref=object_ref,
            context_refs=context_refs,
            evidence_refs=evidence_refs,
            open_findings=open_findings,
            requested_scope=requested_scope,
            prohibited_consequences=prohibited_consequences,
            predecessor_receipt_ref=predecessor_receipt_ref,
            authority_transfer=False,
        )


@dataclass(frozen=True)
class LearningCandidate:
    experience_ref: str
    ocs_id: str
    status: str
    authority_delta: int = 0


class LPEPort:
    """Local learning port without authority or foreign-state mutation."""

    def consolidate(
        self,
        candidate: LearningCandidate,
        *,
        verified: bool,
    ) -> LearningCandidate:
        if candidate.authority_delta != 0:
            raise PermissionError("learning cannot expand authority")
        return LearningCandidate(
            experience_ref=candidate.experience_ref,
            ocs_id=candidate.ocs_id,
            status="VERIFIED" if verified else "REJECTED",
            authority_delta=0,
        )


@dataclass(frozen=True)
class ClosureReceipt:
    block_result: str
    reservations: tuple[str, ...]
    next_owner: str
    authorized_next_scope: str
    prohibited_consequences: tuple[str, ...]


class ReceiptClosure:
    def close(
        self,
        *,
        block_result: str,
        reservations: tuple[str, ...],
        next_owner: str,
        authorized_next_scope: str,
        prohibited_consequences: tuple[str, ...],
    ) -> ClosureReceipt:
        return ClosureReceipt(
            block_result=block_result,
            reservations=reservations,
            next_owner=next_owner,
            authorized_next_scope=authorized_next_scope,
            prohibited_consequences=prohibited_consequences,
        )
