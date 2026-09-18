from __future__ import annotations

from dataclasses import replace

import pytest

from app.cognitive_validation.action_receipt import (
    ActionCognitiveReceiptError,
    ActionCognitiveReceiptIssuer,
    ActionReceiptLedger,
)
from app.cognitive_validation.bootstrap_binding import BootstrapCognitiveBinding
from app.cognitive_validation.mission_receipt import MissionCognitiveReceiptIssuer


def binding() -> BootstrapCognitiveBinding:
    return BootstrapCognitiveBinding(
        binding_id="binding:coi4-001",
        mission_id="mission-001",
        ocs_id="NOESIS",
        ocs_instance_id="noesis-runtime-001",
        generation=9,
        cognitive_entrypoint="UNIVERSAL_COGNITIVE_ENTRYPOINT",
        brain_path="AB0-AB13/canonical",
        authority_ref="authority:noesis:mission-001",
        state_namespace="state:noesis",
        memory_namespace="memory:noesis",
    )


def mission_issuer() -> MissionCognitiveReceiptIssuer:
    return MissionCognitiveReceiptIssuer(
        signing_secret=b"coi3-test-secret",
        clock=lambda: 1_700_000_000.0,
        nonce_factory=lambda: "mission-nonce",
    )


def mission_receipt():
    return mission_issuer().issue(
        binding(),
        intent="execute governed capability",
        state_revision="state-r44",
        state_hash="state-hash-001",
        cognition_cycle_id="cycle-001",
    )


def action_issuer(*, clock=lambda: 1_700_000_001.0, ledger=None):
    return ActionCognitiveReceiptIssuer(
        signing_secret=b"coi4-test-secret",
        mission_issuer=mission_issuer(),
        ledger=ledger,
        clock=clock,
        nonce_factory=lambda: "action-nonce",
        ttl_seconds=60,
    )


def issue_action(issuer):
    return issuer.issue(
        mission_receipt(),
        plan_hash="plan-hash-001",
        action_digest="action-digest-001",
        capability_id="github",
        capability_version="v1",
        adapter_version="adapter-v1",
        authority_requirements=("repo:write",),
        state_hash="state-hash-001",
        policy_version="policy-v1",
    )


def test_action_receipt_binds_exact_context_and_never_grants_authority() -> None:
    issuer = action_issuer()
    receipt = issue_action(issuer)
    assert receipt.mission_id == "mission-001"
    assert receipt.ocs_id == "NOESIS"
    assert receipt.capability_id == "github"
    assert receipt.action_digest == "action-digest-001"
    assert receipt.authority_requirements == ("repo:write",)
    assert receipt.status == "ISSUED"
    assert receipt.authority_granted is False
    assert receipt.effects_permitted is False
    assert issuer.verify(receipt) is True


def test_invalid_mission_receipt_is_denied() -> None:
    bad = replace(mission_receipt(), state_hash="tampered")
    with pytest.raises(ActionCognitiveReceiptError, match="invalid_mission_receipt"):
        action_issuer().issue(
            bad,
            plan_hash="plan",
            action_digest="action",
            capability_id="github",
            capability_version="v1",
            adapter_version="v1",
            authority_requirements=("repo:write",),
            state_hash="tampered",
            policy_version="p1",
        )


def test_state_changed_after_mission_cognition_is_denied() -> None:
    with pytest.raises(ActionCognitiveReceiptError, match="stale_or_mismatched_state"):
        action_issuer().issue(
            mission_receipt(),
            plan_hash="plan",
            action_digest="action",
            capability_id="github",
            capability_version="v1",
            adapter_version="v1",
            authority_requirements=("repo:write",),
            state_hash="state-hash-CHANGED",
            policy_version="p1",
        )


def test_tampering_capability_adapter_action_or_policy_invalidates_receipt() -> None:
    issuer = action_issuer()
    receipt = issue_action(issuer)
    assert issuer.verify(replace(receipt, capability_id="notion")) is False
    assert issuer.verify(replace(receipt, adapter_version="adapter-v2")) is False
    assert issuer.verify(replace(receipt, action_digest="different")) is False
    assert issuer.verify(replace(receipt, policy_version="policy-v2")) is False


def test_expired_receipt_is_denied() -> None:
    issuer = action_issuer()
    receipt = issue_action(issuer)
    assert issuer.verify(receipt, now=receipt.expires_at) is False
    with pytest.raises(ActionCognitiveReceiptError, match="invalid_expired_or_consumed"):
        issuer.consume(receipt, now=receipt.expires_at)


def test_consumption_is_single_use_and_replay_is_denied() -> None:
    ledger = ActionReceiptLedger()
    issuer = action_issuer(ledger=ledger)
    receipt = issue_action(issuer)
    consumed = issuer.consume(receipt)
    assert consumed.status == "CONSUMED"
    assert issuer.verify(receipt) is False
    with pytest.raises(ActionCognitiveReceiptError, match="invalid_expired_or_consumed"):
        issuer.consume(receipt)


def test_shared_ledger_denies_replay_across_issuer_instances() -> None:
    ledger = ActionReceiptLedger()
    first = action_issuer(ledger=ledger)
    second = action_issuer(ledger=ledger)
    receipt = issue_action(first)
    first.consume(receipt)
    assert second.verify(receipt) is False


def test_receipt_cannot_be_promoted_to_authority_or_effect_permission() -> None:
    issuer = action_issuer()
    receipt = issue_action(issuer)
    assert issuer.verify(replace(receipt, authority_granted=True)) is False
    assert issuer.verify(replace(receipt, effects_permitted=True)) is False


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("plan_hash", "", "plan_hash_required"),
        ("action_digest", "", "action_digest_required"),
        ("capability_id", "", "capability_id_required"),
        ("capability_version", "", "capability_version_required"),
        ("adapter_version", "", "adapter_version_required"),
        ("policy_version", "", "policy_version_required"),
    ],
)
def test_required_action_context_fails_closed(field, value, match) -> None:
    kwargs = dict(
        plan_hash="plan",
        action_digest="action",
        capability_id="github",
        capability_version="v1",
        adapter_version="v1",
        authority_requirements=("repo:write",),
        state_hash="state-hash-001",
        policy_version="p1",
    )
    kwargs[field] = value
    with pytest.raises(ActionCognitiveReceiptError, match=match):
        action_issuer().issue(mission_receipt(), **kwargs)


def test_authority_requirements_must_be_declared_but_do_not_grant_authority() -> None:
    with pytest.raises(ActionCognitiveReceiptError, match="authority_requirements_required"):
        action_issuer().issue(
            mission_receipt(),
            plan_hash="plan",
            action_digest="action",
            capability_id="github",
            capability_version="v1",
            adapter_version="v1",
            authority_requirements=(),
            state_hash="state-hash-001",
            policy_version="p1",
        )
