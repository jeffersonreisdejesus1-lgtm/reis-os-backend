from __future__ import annotations

# ruff: noqa: E501, I001

from dataclasses import replace
from time import sleep, time

import pytest

from app.universal_kernel.contracts import (
    ActionProposal,
    Evidence,
    ReversibilityClass,
    RiskLevel,
    SideEffectClass,
    StateRecord,
    VerifiedCheckpoint,
)
from app.universal_kernel.governance import (
    AssuranceReceiptRegistry,
    AuthorityLease,
    AuthorityLeaseManager,
    CapabilityRegistry,
    EvidenceEngine,
    GovernanceEngine,
    IdentityConstitutionLoader,
    OCSIdentity,
)
from app.universal_kernel.state_trace import StateCore
from tools.package_sha256_manifest import build_manifest, verify_manifest


def _governance(*, expires_at: float | None = None, evidence_engine: EvidenceEngine | None = None):
    identities = IdentityConstitutionLoader(
        (
            OCSIdentity(
                ocs="SOFIA",
                specialty="software_engineering",
                constitution_version="r1",
                allowed_capabilities=frozenset({"repo.write"}),
            ),
        )
    )
    capabilities = CapabilityRegistry()
    capabilities.register("SOFIA", frozenset({"repo.write"}))
    leases = AuthorityLeaseManager()
    issued = time() - 1
    leases.issue(
        AuthorityLease(
            lease_id="lease:ext",
            ocs="SOFIA",
            capability="repo.write",
            expires_at=time() + 60 if expires_at is None else expires_at,
            actor="SOFIA",
            issued_at=issued,
            not_before=issued,
            scope=("repo.write",),
            tenant="ext",
            context_ref="context:ext",
            authority_ref="authority:ext",
            policy_snapshot="revision:1",
            action_binding="repository.write",
            object_ref_or_selector="object:ext",
            trace_ref="trace:ext",
            max_uses=1,
        )
    )
    engine = evidence_engine or EvidenceEngine()
    return GovernanceEngine(identities, capabilities, engine, leases), leases


def _proposal(*, risk: RiskLevel = RiskLevel.LOW, evidence: tuple[Evidence, ...] | None = None):
    return ActionProposal(
        action_id="action:ext",
        actor="SOFIA",
        ocs="SOFIA",
        capability="repo.write",
        operation="write",
        payload={"value": 1},
        risk=risk,
        lease_id="lease:ext",
        evidence=(Evidence("evidence:ext", True, "AGORA"),) if evidence is None else evidence,
        action_type="repository.write",
        issued_at=time(),
        csp_ref="csp://sofia/current",
        object_ref="object:ext",
        tenant="ext",
        context_ref="context:ext",
        scope=("repo.write",),
        authority_ref="authority:ext",
        policy_snapshot="revision:1",
        idempotency_key="idem:ext",
        expected_effect="repository_write",
        side_effect_class=SideEffectClass.MATERIAL,
        reversibility_class=ReversibilityClass.REVERSIBLE,
        recovery_ref="recovery:ext",
        expires_at=time() + 30,
        evidence_assessment_ref="assessment:ext",
        trace_id="trace:ext",
    )


def test_f_ext_002_revoked_after_reservation_is_denied_at_effect_boundary() -> None:
    governance, leases = _governance()
    decision = governance.authorize(_proposal())
    assert decision.envelope is not None
    reserved = governance.reserve_authority(decision.envelope)
    assert reserved.envelope is not None
    leases.revoke("lease:ext")

    mutated = False
    with pytest.raises(ValueError, match="lease_revoked"):
        with governance.material_effect_guard(reserved.envelope):
            mutated = True
    assert not mutated


def test_f_ext_002_expired_after_reservation_is_denied_at_effect_boundary() -> None:
    governance, _ = _governance(expires_at=time() + 0.15)
    proposal = replace(_proposal(), expires_at=time() + 0.10)
    decision = governance.authorize(proposal)
    assert decision.envelope is not None
    reserved = governance.reserve_authority(decision.envelope)
    assert reserved.envelope is not None
    sleep(0.2)

    mutated = False
    with pytest.raises(ValueError, match="lease_expired|envelope_expired"):
        with governance.material_effect_guard(reserved.envelope):
            mutated = True
    assert not mutated


def test_f_ext_003_fabricated_nominal_assurance_no_longer_authorizes_high_risk() -> None:
    governance, _ = _governance()
    result = governance.authorize(
        _proposal(
            risk=RiskLevel.HIGH,
            evidence=(Evidence("fabricated:pass", True, "AGORA"),),
        )
    )
    assert result.decision.value == "hold"
    assert result.reason == "independent_assurance_required"


def test_f_ext_003_authenticated_receipt_is_bound_to_object_and_revision() -> None:
    registry = AssuranceReceiptRegistry(b"test-assurance-key")
    registry.issue(
        receipt_id="receipt:1",
        evidence_ref="assurance:1",
        object_ref="object:ext",
        policy_snapshot="revision:1",
        assurer="AGORA",
        verdict_passed=True,
    )
    governance, _ = _governance(evidence_engine=EvidenceEngine(registry))
    result = governance.authorize(
        _proposal(
            risk=RiskLevel.HIGH,
            evidence=(Evidence("assurance:1", True, "AGORA"),),
        )
    )
    assert result.decision.value == "allow"

    wrong_revision = replace(
        _proposal(
            risk=RiskLevel.HIGH,
            evidence=(Evidence("assurance:1", True, "AGORA"),),
        ),
        policy_snapshot="revision:2",
    )
    held = governance.authorize(wrong_revision)
    assert held.decision.value == "hold"


def test_f_ext_004_verified_true_without_statecore_provenance_is_rejected() -> None:
    core = StateCore()
    forged = VerifiedCheckpoint(
        "forged",
        StateRecord(
            state_id="state:forged",
            ocs="SOFIA",
            version=1,
            predecessor=None,
            payload={"forged": True},
            verified=True,
        ),
    )
    with pytest.raises(ValueError, match="verified_checkpoint_source_missing"):
        core.restore_verified(forged)


def test_f_ext_004_checkpoint_matching_existing_verified_state_can_restore() -> None:
    core = StateCore()
    source = StateRecord(
        state_id="state:trusted",
        ocs="SOFIA",
        version=1,
        predecessor=None,
        payload={"safe": True},
        verified=True,
    )
    core.write(
        source,
        lambda stored: stored == source,
        actor_ocs_id="SOFIA",
        target_namespace="state://SOFIA/runtime",
        state_ref=source.state_id,
        authority_context="authority:test",
    )
    restored = core.restore_verified(VerifiedCheckpoint("checkpoint:trusted", source))
    assert restored.payload == source.payload
    assert restored.predecessor == source.state_id
    assert restored.version == 2


def test_f_ext_005_manifest_is_generated_from_final_transport_content(tmp_path) -> None:
    (tmp_path / "native").mkdir()
    (tmp_path / "native" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("corpus\n", encoding="utf-8")
    manifest = build_manifest(tmp_path)
    verify_manifest(tmp_path)
    text = manifest.read_text(encoding="utf-8")
    assert "native/a.py" in text
    assert "README.md" in text
    assert "oldv04/" not in text

    (tmp_path / "native" / "a.py").unlink()
    with pytest.raises(ValueError, match="package_manifest_missing_files"):
        verify_manifest(tmp_path)
