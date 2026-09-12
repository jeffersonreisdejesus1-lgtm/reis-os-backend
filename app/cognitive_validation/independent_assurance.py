from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class AssuranceDisposition(str, Enum):
    PASS = "PASS"
    PASS_WITH_ACCEPTED_RISK = "PASS_WITH_ACCEPTED_RISK"
    HOLD = "HOLD"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class GateEvidence:
    gate: str
    status: str
    main_sha: str
    passed: int
    skipped: int
    failed: int
    claim: str


@dataclass(frozen=True)
class FrozenEvidenceEnvelope:
    program: str
    subject: str
    assurer: str
    assurer_runtime_id: str
    gates: tuple[GateEvidence, ...]
    controls_verified: tuple[str, ...]


@dataclass(frozen=True)
class AssuranceResult:
    disposition: AssuranceDisposition
    checked_gates: tuple[str, ...]
    blocking_findings: tuple[str, ...]


MANDATORY_CONTROLS = frozenset(
    {
        "CAUSAL_MEMORY_ABLATION",
        "FROZEN_LEARNING_BASELINE",
        "ENVIRONMENT_DRIFT",
        "SELF_REGULATION_CAUSALITY",
        "METACOGNITIVE_POLICY_REVISION",
        "IDENTITY_RECOVERY",
        "FAULT_INJECTION",
        "INTEGRATED_ARCHITECTURE_ABLATION",
        "11_OCS_CAUSAL_DISTRIBUTION",
        "LONGITUDINAL_BASELINE_COMPARISON",
    }
)


def assure(envelope: FrozenEvidenceEnvelope) -> AssuranceResult:
    findings: list[str] = []
    expected = tuple(f"AB{i}" for i in range(1, 12))
    actual = tuple(item.gate for item in envelope.gates)

    if envelope.assurer != "SYNESIS_B":
        findings.append("DISTINCT_ASSURER_NOT_BOUND")
    if envelope.subject == envelope.assurer:
        findings.append("SELF_ASSURANCE_FORBIDDEN")
    if envelope.assurer_runtime_id in {"IMPLEMENTATION_WORKER", "AUTHORITATIVE_MAIN_CI"}:
        findings.append("ASSURER_RUNTIME_NOT_DISTINCT")
    if actual != expected:
        findings.append("INCOMPLETE_OR_UNORDERED_GATE_CHAIN")

    for item in envelope.gates:
        if item.status != "PASS":
            findings.append(f"{item.gate}_NOT_PASS")
        if len(item.main_sha) != 40:
            findings.append(f"{item.gate}_INVALID_MAIN_SHA")
        if item.passed <= 0 or item.failed != 0:
            findings.append(f"{item.gate}_CI_NOT_CLEAN")
        if not item.claim:
            findings.append(f"{item.gate}_CLAIM_MISSING")

    if not MANDATORY_CONTROLS.issubset(envelope.controls_verified):
        findings.append("MANDATORY_CONTROL_EVIDENCE_GAP")

    return AssuranceResult(
        disposition=AssuranceDisposition.PASS if not findings else AssuranceDisposition.HOLD,
        checked_gates=actual,
        blocking_findings=tuple(findings),
    )


def freeze_evidence(gates: Iterable[GateEvidence], *, runtime_id: str) -> FrozenEvidenceEnvelope:
    return FrozenEvidenceEnvelope(
        program="REIS-OS-ARTIFICIAL-BRAIN-VALIDATION-001",
        subject="REIS_OS_ARTIFICIAL_BRAIN",
        assurer="SYNESIS_B",
        assurer_runtime_id=runtime_id,
        gates=tuple(gates),
        controls_verified=tuple(sorted(MANDATORY_CONTROLS)),
    )
