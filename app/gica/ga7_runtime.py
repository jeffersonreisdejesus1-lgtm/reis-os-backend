from __future__ import annotations

from dataclasses import dataclass

from app.gica.ga7_authority import Ga7Authority, Ga7AuthorityToken
from app.gica.ga7_controls import Ga7BudgetControl, Ga7BudgetEnvelope
from app.gica.ga7_corpus import Ga7Baseline, Ga7Corpus, Ga7CorpusBinder
from app.gica.ga7_ledger import Ga7Ledger, Ga7LedgerError
from app.gica.ga7_metrics import Ga7Metrics
from app.gica.ga7_types import (
    BOUND_HEAD,
    Ga7CaseState,
    Ga7DiscoveryCaseInput,
    Ga7DiscoveryCaseResult,
    Ga7Disposition,
    Ga7EpistemicClass,
    Ga7ReceiptType,
)

UNRESOLVED_STATES = {
    Ga7CaseState.UNKNOWN,
    Ga7CaseState.RECONCILING,
    Ga7CaseState.STILL_UNKNOWN,
}


@dataclass(frozen=True)
class Ga7RuntimeManifest:
    runtime_id: str
    runtime_version: str
    exact_head: str
    specialties: frozenset[str]
    capabilities: frozenset[str]
    material_effect_capable: bool = False
    max_parallelism: int = 1
    max_recursion_depth: int = 0
    can_merge: bool = False
    can_promote: bool = False
    can_founder: bool = False
    timeout_supported: bool = True
    metrics_supported: bool = True


@dataclass(frozen=True)
class Ga7PreflightResult:
    status: str
    reasons: tuple[str, ...]
    exact_head: str


@dataclass
class Ga7HostBinding:
    manifest: Ga7RuntimeManifest
    ledger: Ga7Ledger
    trust_provisioned: bool

    def preflight(self) -> Ga7PreflightResult:
        reasons: list[str] = []
        if self.manifest.exact_head != BOUND_HEAD:
            reasons.append("wrong_head")
        if self.manifest.material_effect_capable:
            reasons.append("material_capability")
        if self.manifest.max_parallelism != 1:
            reasons.append("parallelism")
        if self.manifest.max_recursion_depth != 0:
            reasons.append("recursion")
        if self.manifest.can_merge or self.manifest.can_promote or self.manifest.can_founder:
            reasons.append("promotion_or_founder_capability")
        if not self.trust_provisioned:
            reasons.append("trust_unavailable")
        if not self.ledger.path.exists():
            reasons.append("ledger_unavailable")
        status = "HOLD" if reasons else "PASS_CANDIDATE"
        return Ga7PreflightResult(status, tuple(reasons), self.manifest.exact_head)


class Ga7Runtime:
    def __init__(self, ledger: Ga7Ledger, manifest: Ga7RuntimeManifest) -> None:
        self.ledger = ledger
        self.manifest = manifest
        self._busy = False
        self.authority = Ga7Authority()
        self.corpus = Ga7CorpusBinder()
        self.metrics = Ga7Metrics()

    def execute(
        self,
        case: Ga7DiscoveryCaseInput,
        token: Ga7AuthorityToken | None,
        envelope: Ga7BudgetEnvelope,
        corpus: Ga7Corpus | None,
        baseline: Ga7Baseline | None,
        *,
        request_parallel: bool = False,
        request_recursion: bool = False,
        request_material: bool = False,
        request_ga7_entry: bool = False,
        request_self_promote: bool = False,
        force_timeout: bool = False,
        force_unknown: bool = False,
        force_readback_failure: bool = False,
    ) -> Ga7DiscoveryCaseResult:
        if request_parallel or self._busy:
            return self._terminal(case, Ga7CaseState.DENIED, Ga7Disposition.DENIED, "parallelism_denied")
        if request_recursion:
            return self._terminal(case, Ga7CaseState.DENIED, Ga7Disposition.DENIED, "recursion_denied")
        if request_ga7_entry:
            return self._terminal(case, Ga7CaseState.DENIED, Ga7Disposition.DENIED, "ga7_entry_denied")
        if request_self_promote:
            return self._terminal(case, Ga7CaseState.DENIED, Ga7Disposition.DENIED, "self_promotion_denied")

        valid, reason = case.validate()
        if not valid:
            return self._terminal(case, Ga7CaseState.DENIED, Ga7Disposition.DENIED, reason)

        self.ledger.bind_case(case)
        self.ledger.append_receipt(
            receipt_id=f"case:{case.case_key()}",
            case_key=case.case_key(),
            receipt_type=Ga7ReceiptType.GA7_DISCOVERY_CASE,
            epistemic=Ga7EpistemicClass.DECLARED,
            payload={"identity": case.identity_hash()},
        )

        admission = self.authority.admit(case, token, self.ledger)
        if not admission.admitted:
            return self._terminal(case, Ga7CaseState.DENIED, Ga7Disposition.DENIED, admission.reason)

        binding = self.corpus.bind(case, corpus, baseline)
        if not binding.ok:
            state = Ga7CaseState.ABORTED if binding.reason == "sealed_holdout_contamination" else Ga7CaseState.HOLD
            disp = Ga7Disposition.ABORTED if state is Ga7CaseState.ABORTED else Ga7Disposition.HOLD
            return self._terminal(case, state, disp, binding.reason)

        budget = Ga7BudgetControl(envelope, self.ledger, case.case_key())
        if not budget.active:
            return self._terminal(case, Ga7CaseState.HOLD, Ga7Disposition.HOLD, budget.reason)

        missing = [item for item in case.participating_specialties if item not in self.manifest.specialties]
        missing += [item for item in case.capability_bindings if item not in self.manifest.capabilities]
        if missing:
            return self._terminal(case, Ga7CaseState.HOLD, Ga7Disposition.HOLD, "unavailable_specialty_or_capability")

        allowed, budget_reason = budget.allow("case")
        if not allowed:
            return self._terminal(case, Ga7CaseState.HOLD, Ga7Disposition.STOPPED, budget_reason)

        if request_material or case.effect_class == "MATERIAL":
            self.ledger.append_receipt(
                receipt_id=f"deny-effect:{case.case_key()}",
                case_key=case.case_key(),
                receipt_type=Ga7ReceiptType.EFFECT_DENIAL_OR_NONMATERIAL_EFFECT,
                epistemic=Ga7EpistemicClass.OBSERVED,
                payload={"request": "material", "dispatched": False},
            )
            return self._terminal(case, Ga7CaseState.DENIED, Ga7Disposition.DENIED, "material_effect_denied")

        if force_timeout:
            return self._terminal(case, Ga7CaseState.HOLD, Ga7Disposition.HOLD, "timeout")
        if force_unknown:
            self.ledger.set_state(case.case_key(), Ga7CaseState.UNKNOWN)
            return Ga7DiscoveryCaseResult(
                case_key=case.case_key(),
                identity_hash=case.identity_hash(),
                state=Ga7CaseState.UNKNOWN,
                disposition=Ga7Disposition.UNKNOWN,
                failure="unknown",
                authority_result="unknown",
            )

        self._busy = True
        try:
            self.ledger.set_state(case.case_key(), Ga7CaseState.RUNNING)
            self.ledger.append_receipt(
                receipt_id=f"compose:{case.case_key()}",
                case_key=case.case_key(),
                receipt_type=Ga7ReceiptType.OCS_COMPOSITION,
                epistemic=Ga7EpistemicClass.OBSERVED,
                payload={"specialties": list(case.participating_specialties)},
            )
            self.ledger.append_receipt(
                receipt_id=f"action:{case.case_key()}",
                case_key=case.case_key(),
                receipt_type=Ga7ReceiptType.ACTION,
                epistemic=Ga7EpistemicClass.OBSERVED,
                payload={"nonmaterial": True},
            )
            if force_readback_failure:
                return self._terminal(case, Ga7CaseState.HOLD, Ga7Disposition.HOLD, "evidence_readback_failure")
            snap = self.metrics.snapshot(self.ledger, case.case_key())
            result = Ga7DiscoveryCaseResult(
                case_key=case.case_key(),
                identity_hash=case.identity_hash(),
                state=Ga7CaseState.OBSERVED,
                disposition=Ga7Disposition.OBSERVED,
                observed="nonmaterial_fixture",
                composition=case.participating_specialties,
                authority_result="admitted",
                metrics={"receipt_count": snap.receipt_count, "hash": snap.snapshot_hash},
                evidence_refs=(f"case:{case.case_key()}",),
            )
            self.ledger.finalize(result)
            self.ledger.append_receipt(
                receipt_id=f"readback:{case.case_key()}",
                case_key=case.case_key(),
                receipt_type=Ga7ReceiptType.EVIDENCE_READBACK,
                epistemic=Ga7EpistemicClass.REPRODUCED,
                payload={"ok": True},
            )
            return result
        finally:
            self._busy = False

    def replay(self, case: Ga7DiscoveryCaseInput) -> Ga7DiscoveryCaseResult:
        existing = self.ledger.load_result(case.case_key())
        if existing is not None:
            return existing
        raise Ga7LedgerError("no_canonical_result")

    def reconcile_unknown(self, case: Ga7DiscoveryCaseInput) -> Ga7DiscoveryCaseResult:
        self.ledger.set_state(case.case_key(), Ga7CaseState.RECONCILING)
        existing = self.ledger.load_result(case.case_key())
        if existing is not None and existing.state not in UNRESOLVED_STATES:
            self.ledger.append_receipt(
                receipt_id=f"recon-resolved:{case.case_key()}",
                case_key=case.case_key(),
                receipt_type=Ga7ReceiptType.RECONCILIATION,
                epistemic=Ga7EpistemicClass.REPRODUCED,
                payload={"resolved": existing.state.value},
            )
            return existing
        self.ledger.append_receipt(
            receipt_id=f"recon:{case.case_key()}",
            case_key=case.case_key(),
            receipt_type=Ga7ReceiptType.RECONCILIATION,
            epistemic=Ga7EpistemicClass.INFERRED,
            payload={"still_unknown": True},
        )
        return self._terminal(case, Ga7CaseState.STILL_UNKNOWN, Ga7Disposition.UNKNOWN, "still_unknown")

    def capture_learning(self, case: Ga7DiscoveryCaseInput, observation: str) -> None:
        self.ledger.put_learning(
            f"learn:{case.case_key()}",
            case.case_key(),
            {
                "observation": observation,
                "hypothesis": "pilot-only",
                "evidence_refs": [f"case:{case.case_key()}"],
                "authority_impact": "NONE",
            },
        )
        self.ledger.append_receipt(
            receipt_id=f"learn:{case.case_key()}",
            case_key=case.case_key(),
            receipt_type=Ga7ReceiptType.LEARNING,
            epistemic=Ga7EpistemicClass.INFERRED,
            payload={"authority_impact": "NONE"},
        )

    def _terminal(self, case, state, disposition, failure) -> Ga7DiscoveryCaseResult:
        result = Ga7DiscoveryCaseResult(
            case_key=case.case_key(),
            identity_hash=case.identity_hash(),
            state=state,
            disposition=disposition,
            failure=failure,
            authority_result=failure,
        )
        try:
            self.ledger.bind_case(case)
            self.ledger.finalize(result)
        except Ga7LedgerError:
            pass
        return result
