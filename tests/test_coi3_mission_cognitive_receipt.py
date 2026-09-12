from __future__ import annotations

from dataclasses import replace

import pytest

from app.cognitive_validation.bootstrap_binding import BootstrapCognitiveBinding
from app.cognitive_validation.mission_receipt import (
    MissionCognitiveReceiptError,
    MissionCognitiveReceiptIssuer,
)


def binding() -> BootstrapCognitiveBinding:
    return BootstrapCognitiveBinding(
        binding_id="binding:coi3-001",
        mission_id="mission-001",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-001",
        generation=8,
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        brain_path="AB0-AB13/canonical",
        authority_ref="authority:noesis:mission-001",
        state_namespace="state:noesis",
        memory_namespace="memory:noesis",
    )


def issuer() -> MissionCognitiveReceiptIssuer:
    return MissionCognitiveReceiptIssuer(
        signing_secret=b"coi3-test-secret",
        clock=lambda: 1_700_000_000.0,
        nonce_factory=lambda: "nonce-001",
    )


def test_issues_verifiable_receipt_after_canonical_cognition() -> None:
    receipt = issuer().issue(
        binding(),
        intent="resolve governed mission",
        state_revision="state-r43",
        state_hash="state-hash-001",
        cognition_cycle_id="cycle-001",
    )
    assert receipt.mission_id == "mission-001"
    assert receipt.ocs_id == "NOESIS"
    assert receipt.ocs_instance_id == "noesis-runtime-001"
    assert receipt.generation == 8
    assert receipt.brain_version == "AB0-AB13/canonical"
    assert receipt.status == "ISSUED"
    assert receipt.authority_granted is False
    assert receipt.effects_permitted is False
    assert issuer().verify(receipt) is True


def test_receipt_binds_intent_without_storing_plaintext() -> None:
    receipt = issuer().issue(
        binding(),
        intent="sensitive mission intent",
        state_hash="state-hash-001",
        cognition_cycle_id="cycle-001",
    )
    assert receipt.intent_hash
    assert "sensitive mission intent" not in repr(receipt)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("intent", "", "intent_required"),
        ("state_hash", "", "state_hash_required"),
        ("cognition_cycle_id", "", "cycle_required"),
    ],
)
def test_required_receipt_context_fails_closed(field: str, value: str, match: str) -> None:
    kwargs = {
        "intent": "resolve governed mission",
        "state_hash": "state-hash-001",
        "cognition_cycle_id": "cycle-001",
    }
    kwargs[field] = value
    with pytest.raises(MissionCognitiveReceiptError, match=match):
        issuer().issue(binding(), **kwargs)


def test_bootstrap_that_does_not_require_cognition_is_denied() -> None:
    bad = replace(binding(), cognitive_path_required=False)
    with pytest.raises(MissionCognitiveReceiptError, match="cognitive_path_not_required"):
        issuer().issue(
            bad,
            intent="resolve governed mission",
            state_hash="state-hash-001",
            cognition_cycle_id="cycle-001",
        )


def test_bootstrap_cannot_pregrant_authority() -> None:
    bad = replace(binding(), cognition_grants_authority=True)
    with pytest.raises(MissionCognitiveReceiptError, match="privilege_violation"):
        issuer().issue(
            bad,
            intent="resolve governed mission",
            state_hash="state-hash-001",
            cognition_cycle_id="cycle-001",
        )


def test_tampered_receipt_is_rejected() -> None:
    receipt = issuer().issue(
        binding(),
        intent="resolve governed mission",
        state_hash="state-hash-001",
        cognition_cycle_id="cycle-001",
    )
    assert issuer().verify(replace(receipt, state_hash="tampered")) is False


def test_tampered_signature_is_rejected() -> None:
    receipt = issuer().issue(
        binding(),
        intent="resolve governed mission",
        state_hash="state-hash-001",
        cognition_cycle_id="cycle-001",
    )
    assert issuer().verify(replace(receipt, signature="00" * 32)) is False


def test_receipt_cannot_be_promoted_to_authority_or_effect_permission() -> None:
    receipt = issuer().issue(
        binding(),
        intent="resolve governed mission",
        state_hash="state-hash-001",
        cognition_cycle_id="cycle-001",
    )
    assert issuer().verify(replace(receipt, authority_granted=True)) is False
    assert issuer().verify(replace(receipt, effects_permitted=True)) is False
