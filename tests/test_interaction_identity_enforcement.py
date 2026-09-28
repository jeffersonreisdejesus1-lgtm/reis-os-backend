from __future__ import annotations

from dataclasses import replace

import pytest

from app.universal_kernel.identity import IdentityBindingStatus, IdentityKernelGuard
from app.universal_kernel.interaction_identity import (
    IdentityClaimSource,
    InteractionIdentityEnforcer,
    InteractionIdentityStatus,
)


@pytest.mark.parametrize(
    "source",
    [
        IdentityClaimSource.USER,
        IdentityClaimSource.PROMPT,
        IdentityClaimSource.HANDOFF,
        IdentityClaimSource.HOST,
        IdentityClaimSource.INTERNAL_CONFIG,
    ],
)
def test_claim_source_never_proves_identity_without_binding(
    source: IdentityClaimSource,
) -> None:
    result = InteractionIdentityEnforcer(IdentityKernelGuard()).readback(
        run_id="run:unbound",
        claimed_ocs="ÍRIS",
        claim_source=source,
        host="ChatGPT",
    )

    assert result.status is InteractionIdentityStatus.UNVERIFIED
    assert not result.canonical_identity_disclosable
    assert result.ocs_canonical_name is None
    assert result.ocs_id is None
    assert "ocs_canonical_name" not in result.to_public_dict()
    assert "ocs_id" not in result.to_public_dict()


def test_screenshot_regression_user_says_this_ocs_is_iris_but_no_binding() -> None:
    result = InteractionIdentityEnforcer(IdentityKernelGuard()).readback(
        run_id="run:screenshot",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.USER,
        host="ChatGPT",
    )

    assert result.to_public_dict() == {
        "identity_status": "unverified",
        "reason": "identity_binding_readback_missing",
        "run_id": "run:screenshot",
        "claim_source": "user",
    }


def test_verified_binding_releases_canonical_identity_fields() -> None:
    guard = IdentityKernelGuard()
    binding = guard.bind_active_identity(
        run_id="run:iris",
        ocs_id="ÍRIS",
        host="ChatGPT",
        session_context="session:iris",
    )

    result = InteractionIdentityEnforcer(guard).readback(
        run_id="run:iris",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.USER,
        host="ChatGPT",
    )

    assert result.status is InteractionIdentityStatus.VERIFIED
    assert result.canonical_identity_disclosable
    assert result.ocs_canonical_name == binding.ocs_canonical_name
    assert result.ocs_id == binding.ocs_id
    assert result.institution == "REIS OS"
    assert result.binding_hash == guard.audit_log.binding_hash(binding)
    assert result.evidence_source == "kernel_identity_binding_readback"
    assert result.to_public_dict()["ocs_id"] == "ÍRIS"
    assert any(
        event.event_type == "INTERACTION_IDENTITY_READBACK"
        for event in guard.audit_log.events
    )


def test_valid_binding_without_host_is_unverified_and_hides_identity() -> None:
    guard = IdentityKernelGuard()
    guard.bind_active_identity(
        run_id="run:host-omitted",
        ocs_id="ÍRIS",
        host="ChatGPT",
        session_context="session:host-omitted",
    )

    result = InteractionIdentityEnforcer(guard).readback(
        run_id="run:host-omitted",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.USER,
    )

    assert result.status is InteractionIdentityStatus.UNVERIFIED
    assert result.reason == "interaction_host_context_required"
    assert not result.canonical_identity_disclosable
    assert result.ocs_canonical_name is None
    assert result.ocs_id is None
    assert result.binding_hash is None
    assert result.evidence_source is None
    assert "ocs_canonical_name" not in result.to_public_dict()
    assert "ocs_id" not in result.to_public_dict()
    assert "binding_hash" not in result.to_public_dict()
    assert "evidence_source" not in result.to_public_dict()


def test_wrong_claim_holds_and_discloses_no_canonical_id() -> None:
    guard = IdentityKernelGuard()
    guard.bind_active_identity(
        run_id="run:noesis",
        ocs_id="NÓESIS",
        host="ChatGPT",
        session_context="session:noesis",
    )

    result = InteractionIdentityEnforcer(guard).readback(
        run_id="run:noesis",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.USER,
        host="ChatGPT",
    )

    assert result.status is InteractionIdentityStatus.HOLD
    assert result.reason == "active_ocs_identity_mismatch"
    assert not result.canonical_identity_disclosable
    assert "ocs_id" not in result.to_public_dict()
    held = guard.binding_for("run:noesis")
    assert held is not None
    assert held.status is IdentityBindingStatus.HOLD


def test_held_binding_never_discloses_canonical_identity() -> None:
    guard = IdentityKernelGuard()
    guard.bind_active_identity(
        run_id="run:held",
        ocs_id="ÍRIS",
        host="ChatGPT",
        session_context="session:held",
    )
    guard.hold("run:held", "identity_conflict")

    result = InteractionIdentityEnforcer(guard).readback(
        run_id="run:held",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.PROMPT,
        host="ChatGPT",
    )

    assert result.status is InteractionIdentityStatus.HOLD
    assert result.reason == "identity_conflict"
    assert "ocs_canonical_name" not in result.to_public_dict()


def test_tampered_profile_binding_is_held_and_not_disclosed() -> None:
    guard = IdentityKernelGuard()
    original = guard.bind_active_identity(
        run_id="run:tampered",
        ocs_id="ÍRIS",
        host="ChatGPT",
        session_context="session:tampered",
    )
    guard._bindings["run:tampered"] = replace(  # noqa: SLF001 - adversarial fixture
        original,
        identity_ref="identity://forged",
    )

    result = InteractionIdentityEnforcer(guard).readback(
        run_id="run:tampered",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.INTERNAL_CONFIG,
        host="ChatGPT",
    )

    assert result.status is InteractionIdentityStatus.HOLD
    assert result.reason == "identity_profile_mismatch"
    assert result.ocs_id is None


def test_host_claim_cannot_override_bound_host() -> None:
    guard = IdentityKernelGuard()
    guard.bind_active_identity(
        run_id="run:host",
        ocs_id="ÍRIS",
        host="ChatGPT",
        session_context="session:host",
    )

    result = InteractionIdentityEnforcer(guard).readback(
        run_id="run:host",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.HOST,
        host="Claude",
    )

    assert result.status is InteractionIdentityStatus.HOLD
    assert result.reason == "host_identity_context_mismatch"
    assert "ocs_id" not in result.to_public_dict()


def test_explicit_rebind_restores_verifiable_identity_after_hold() -> None:
    guard = IdentityKernelGuard()
    guard.bind_active_identity(
        run_id="run:rebind",
        ocs_id="NÓESIS",
        host="ChatGPT",
        session_context="session:before",
    )
    guard.hold("run:rebind", "identity_conflict")
    guard.rebind(
        run_id="run:rebind",
        ocs_id="ÍRIS",
        host="ChatGPT",
        session_context="session:after",
        reason="explicit_identity_rebind",
    )

    result = InteractionIdentityEnforcer(guard).readback(
        run_id="run:rebind",
        claimed_ocs="ÍRIS",
        claim_source=IdentityClaimSource.INTERNAL_CONFIG,
        host="ChatGPT",
    )

    assert result.status is InteractionIdentityStatus.VERIFIED
    assert result.ocs_id == "ÍRIS"
