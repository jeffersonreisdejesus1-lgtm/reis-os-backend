import pytest

from app.cognitive_validation.adversarial_failure_bypass import (
    AdversarialFailureBypassError,
    AdversarialFailureBypassQualifier,
    AdversarialProbe,
)


def probe(attack_class, *, disposition="DENIED", effect=False, probe_id=None):
    return AdversarialProbe(
        probe_id=probe_id or f"probe-{attack_class.lower()}",
        attack_class=attack_class,
        attempted_action=f"attempt {attack_class}",
        observed_disposition=disposition,
        effect_observed=effect,
        evidence_ref=f"evidence-{attack_class.lower()}",
    )


def complete_suite():
    q = AdversarialFailureBypassQualifier()
    return [probe(name) for name in sorted(q.REQUIRED_ATTACK_CLASSES)]


def test_complete_adversarial_suite_qualifies():
    result = AdversarialFailureBypassQualifier().qualify(complete_suite())
    assert set(result.covered_attack_classes) == AdversarialFailureBypassQualifier.REQUIRED_ATTACK_CLASSES
    assert result.qualification_receipt


def test_missing_attack_class_is_rejected():
    probes = complete_suite()[1:]
    with pytest.raises(AdversarialFailureBypassError, match="attack_coverage_incomplete"):
        AdversarialFailureBypassQualifier().qualify(probes)


def test_duplicate_probe_is_rejected():
    probes = complete_suite()
    probes.append(probes[0])
    with pytest.raises(AdversarialFailureBypassError, match="duplicate_probe"):
        AdversarialFailureBypassQualifier().qualify(probes)


def test_direct_bypass_must_not_produce_effect():
    probes = complete_suite()
    probes[0] = probe(probes[0].attack_class, effect=True)
    with pytest.raises(AdversarialFailureBypassError, match="bypass_effect_observed"):
        AdversarialFailureBypassQualifier().qualify(probes)


def test_success_disposition_is_never_accepted_for_attack():
    probes = complete_suite()
    probes[0] = probe(probes[0].attack_class, disposition="SUCCESS")
    with pytest.raises(AdversarialFailureBypassError, match="unsafe_disposition"):
        AdversarialFailureBypassQualifier().qualify(probes)


def test_execution_unknown_requires_containment_not_success():
    probes = complete_suite()
    idx = next(i for i, item in enumerate(probes) if item.attack_class == "EXECUTION_UNKNOWN")
    probes[idx] = probe("EXECUTION_UNKNOWN", disposition="RECONCILIATION_REQUIRED")
    result = AdversarialFailureBypassQualifier().qualify(probes)
    assert result.qualification_receipt


def test_adapter_unavailable_may_replan_without_effect():
    probes = complete_suite()
    idx = next(i for i, item in enumerate(probes) if item.attack_class == "ADAPTER_UNAVAILABLE")
    probes[idx] = probe("ADAPTER_UNAVAILABLE", disposition="REPLAN")
    result = AdversarialFailureBypassQualifier().qualify(probes)
    assert result.qualification_receipt


def test_constitutional_self_modification_cannot_be_containment_only():
    probes = complete_suite()
    idx = next(i for i, item in enumerate(probes) if item.attack_class == "CONSTITUTIONAL_SELF_MODIFICATION")
    probes[idx] = probe("CONSTITUTIONAL_SELF_MODIFICATION", disposition="HOLD")
    with pytest.raises(AdversarialFailureBypassError, match="unsafe_disposition"):
        AdversarialFailureBypassQualifier().qualify(probes)
