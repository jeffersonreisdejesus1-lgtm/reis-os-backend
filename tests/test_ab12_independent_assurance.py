from dataclasses import FrozenInstanceError

import pytest

from app.cognitive_validation.independent_assurance import (
    AssuranceDisposition,
    GateEvidence,
    assure,
    freeze_evidence,
)


EVIDENCE = (
    GateEvidence("AB1", "PASS", "27512176d498111fb5d84133d6ac9f672a7ea91c", 910, 11, 0, "CLOSED_COGNITIVE_LOOP"),
    GateEvidence("AB2", "PASS", "b99453780f6811e0afe2abb08f91d3bc79da942c", 916, 11, 0, "CAUSAL_MEMORY"),
    GateEvidence("AB3", "PASS", "19b40fcd33baf4ee592b18b861f180086f353004", 923, 11, 0, "LONGITUDINAL_LEARNING"),
    GateEvidence("AB4", "PASS", "0380dddaa2972bfe5f1cc9ded7438e764430da2b", 930, 11, 0, "PLASTICITY"),
    GateEvidence("AB5", "PASS", "3e79878b2fcb1d8f8b72c2452298c4e03ec5c5de", 940, 11, 0, "SELF_REGULATION"),
    GateEvidence("AB6", "PASS", "e430d395cc2748d638556b40f1757f6cb1ec8a14", 956, 11, 0, "METACOGNITIVE_REVISION"),
    GateEvidence("AB7", "PASS", "26d919faa550c090b0dfe091c161bbcde7c1f6c6", 965, 11, 0, "IDENTITY_PRESERVING_ADAPTATION"),
    GateEvidence("AB8", "PASS", "9231b3004b2a1002e062b685d0bd00cef15ed3de", 974, 11, 0, "COGNITIVE_FAILURE_RESILIENCE"),
    GateEvidence("AB9", "PASS", "c0d653bca7f701ada6a03e89b1e34e6e064c5f9c", 980, 11, 0, "INTEGRATED_COGNITIVE_ARCHITECTURE"),
    GateEvidence("AB10", "PASS", "c7dcdfd7350d1384f262e05ab690ed9bda74dd71", 988, 11, 0, "DISTRIBUTED_INTEGRATED_COGNITION"),
    GateEvidence("AB11", "PASS", "8b5f0571079688224c569cf21a7ff73afefc4f64", 992, 11, 0, "LONGITUDINAL_ARTIFICIAL_BRAIN_EVIDENCE"),
)


def test_ab12_synesis_b_passes_complete_frozen_evidence_on_distinct_runtime():
    envelope = freeze_evidence(EVIDENCE, runtime_id="SYNESIS_B_DISTINCT_RENDER_RUNTIME")
    result = assure(envelope)
    assert result.disposition is AssuranceDisposition.PASS
    assert result.blocking_findings == ()
    assert result.checked_gates == tuple(f"AB{i}" for i in range(1, 12))


def test_ab12_evidence_envelope_is_immutable():
    envelope = freeze_evidence(EVIDENCE, runtime_id="SYNESIS_B_DISTINCT_RENDER_RUNTIME")
    with pytest.raises(FrozenInstanceError):
        envelope.assurer = "NOESIS"  # type: ignore[misc]


def test_ab12_rejects_self_or_non_distinct_assurance():
    envelope = freeze_evidence(EVIDENCE, runtime_id="IMPLEMENTATION_WORKER")
    result = assure(envelope)
    assert result.disposition is AssuranceDisposition.HOLD
    assert "ASSURER_RUNTIME_NOT_DISTINCT" in result.blocking_findings


def test_ab12_rejects_incomplete_or_failed_gate_evidence():
    broken = EVIDENCE[:-1]
    envelope = freeze_evidence(broken, runtime_id="SYNESIS_B_DISTINCT_RENDER_RUNTIME")
    result = assure(envelope)
    assert result.disposition is AssuranceDisposition.HOLD
    assert "INCOMPLETE_OR_UNORDERED_GATE_CHAIN" in result.blocking_findings
