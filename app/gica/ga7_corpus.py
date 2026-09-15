from __future__ import annotations

from dataclasses import dataclass

from app.gica.ga7_types import EXPECTED_POLICY, Ga7DiscoveryCaseInput


@dataclass(frozen=True)
class Ga7Corpus:
    ref: str
    version: str
    content_hash: str
    case_ids: frozenset[str]
    holdout_classification: str
    policy_version: str
    bound_head: str
    sealed_ga9_holdout: bool = False


@dataclass(frozen=True)
class Ga7Baseline:
    ref: str
    version: str
    content_hash: str
    kind: str
    readable: bool


@dataclass(frozen=True)
class Ga7BindingReceipt:
    ok: bool
    reason: str


class Ga7CorpusBinder:
    def bind(
        self,
        case: Ga7DiscoveryCaseInput,
        corpus: Ga7Corpus | None,
        baseline: Ga7Baseline | None,
    ) -> Ga7BindingReceipt:
        if corpus is None or not corpus.ref:
            return Ga7BindingReceipt(False, "missing_corpus")
        if corpus.sealed_ga9_holdout or corpus.holdout_classification == "GA9_SEALED":
            return Ga7BindingReceipt(False, "sealed_holdout_contamination")
        if case.discovery_case_id not in corpus.case_ids:
            return Ga7BindingReceipt(False, "corpus_membership_failure")
        if corpus.bound_head != case.bound_head:
            return Ga7BindingReceipt(False, "corpus_wrong_head")
        if corpus.policy_version != EXPECTED_POLICY:
            return Ga7BindingReceipt(False, "corpus_wrong_policy")
        if (
            corpus.ref != case.discovery_corpus_ref
            or corpus.version != case.discovery_corpus_version
        ):
            return Ga7BindingReceipt(False, "corpus_ref_mismatch")
        if not corpus.content_hash:
            return Ga7BindingReceipt(False, "corpus_hash_missing")
        if case.baseline_required:
            if baseline is None or not baseline.ref:
                return Ga7BindingReceipt(False, "missing_baseline")
            if not baseline.readable or baseline.kind == "FABRICATED":
                return Ga7BindingReceipt(False, "fabricated_or_unreadable_baseline")
            if (
                baseline.ref != case.baseline_ref
                or baseline.version != case.baseline_version
            ):
                return Ga7BindingReceipt(False, "baseline_ref_mismatch")
        return Ga7BindingReceipt(True, "bound")
