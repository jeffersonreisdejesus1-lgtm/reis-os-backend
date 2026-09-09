from dataclasses import replace

import pytest

from app.ocs_v1_batch import (
    DecisionStatus,
    EvidenceState,
    GovernanceRequest,
    OCSV1InvariantError,
    OCSV1Runtime,
    PROFILES,
)


def runtime(ocs: str) -> OCSV1Runtime:
    profile = PROFILES[ocs]
    return OCSV1Runtime(
        profile=profile,
        binding_refs=dict(profile.binding_refs),
        derivation_ref=profile.derivation_ref,
    )


def base_request(ocs: str) -> GovernanceRequest:
    profile = PROFILES[ocs]
    governor = profile.governors[0]
    kwargs = dict(
        request_id=f"req:{ocs}:1",
        ocs_id=ocs,
        governor_id=governor.governor_id,
        operation=governor.allowed_operations[0],
        namespace=governor.writable_namespaces[0],
        mutation={governor.owned_state_keys[0]: "ok"},
        expected_state_version=0,
        evidence_state=EvidenceState.CURRENT,
        evidence_ref="evidence:1",
        provenance_ref="provenance:1",
        object_ref="object:1",
        exact_head="0123456789abcdef",
        authority_ref="AUTHORITY:SCOPED",
        package_id="package:1",
    )
    return GovernanceRequest(**kwargs)


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_profile_has_exact_local_roster_and_six_bindings(ocs):
    profile = PROFILES[ocs]
    profile.validate()
    assert len(profile.governors) == 4
    assert len(profile.binding_refs) == 6
    assert all(g.governor_id.startswith(f"GOV-{ocs}-") for g in profile.governors)


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_wrong_derivation_or_binding_fails_closed_at_construction(ocs):
    profile = PROFILES[ocs]
    with pytest.raises(OCSV1InvariantError, match="DERIVATION_REF_MISMATCH"):
        OCSV1Runtime(profile=profile, binding_refs=dict(profile.binding_refs), derivation_ref="NOESIS-ROSTER")
    bad = dict(profile.binding_refs)
    bad["R6_R7_BINDING_REF"] = "wrong"
    with pytest.raises(OCSV1InvariantError, match="R1_R6_BINDING_REF_MISMATCH"):
        OCSV1Runtime(profile=profile, binding_refs=bad, derivation_ref=profile.derivation_ref)


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_cross_ocs_and_cross_owner_writes_deny_zero_mutation(ocs):
    rt = runtime(ocs)
    request = base_request(ocs)
    cross = replace(request, ocs_id="NOESIS")
    receipt = rt.execute(cross)
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.mutation_count == 0
    assert rt.state_version == 0

    governor = PROFILES[ocs].governors[0]
    bad_key = "foreign_key"
    receipt = rt.execute(replace(request, mutation={bad_key: "x"}))
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.reason == "STATE_KEY_OWNERSHIP_VIOLATION"
    assert receipt.mutation_count == 0
    assert rt.state_version == 0


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_promotion_activation_authority_transfer_and_self_assurance_forbidden(ocs):
    rt = runtime(ocs)
    req = base_request(ocs)
    cases = [
        (replace(req, self_assurance_requested=True), "SELF_ASSURANCE_FORBIDDEN"),
        (replace(req, promotion_requested=True), "CANONICAL_PROMOTION_NOT_AUTHORIZED"),
        (replace(req, runtime_activation_requested=True), "RUNTIME_GOVERNOR_ACTIVATION_NOT_AUTHORIZED"),
        (replace(req, authority_transfer_requested=True), "AUTHORITY_TRANSFER_FORBIDDEN"),
    ]
    for request, reason in cases:
        receipt = rt.execute(request)
        assert receipt.status is DecisionStatus.DENIED
        assert receipt.reason == reason
        assert receipt.mutation_count == 0
        assert rt.state_version == 0


@pytest.mark.parametrize("ocs", ["DEDALA", "AGORA", "SOFIA", "METIS", "LYRA"])
def test_non_current_evidence_holds_zero_mutation(ocs):
    rt = runtime(ocs)
    for state in (EvidenceState.STALE, EvidenceState.UNKNOWN, EvidenceState.CONFLICTED):
        receipt = rt.execute(replace(base_request(ocs), evidence_state=state))
        assert receipt.status is DecisionStatus.HOLD
        assert receipt.mutation_count == 0
        assert rt.state_version == 0


def test_dedala_requires_evidence_and_provenance_and_accepts_valid_local_write():
    rt = runtime("DEDALA")
    req = base_request("DEDALA")
    assert rt.execute(replace(req, evidence_ref=None)).reason == "HOLD_EVIDENCE_PROVENANCE_REQUIRED"
    assert rt.execute(replace(req, provenance_ref=None)).reason == "HOLD_EVIDENCE_PROVENANCE_REQUIRED"
    accepted = rt.execute(req)
    assert accepted.status is DecisionStatus.ACCEPTED
    assert accepted.mutation_count == 1


def test_agora_requires_exact_object_head_and_missing_evidence_never_passes():
    rt = runtime("AGORA")
    req = base_request("AGORA")
    assert rt.execute(replace(req, exact_head=None)).reason == "HOLD_EXACT_IMPLEMENTATION_OBJECT_HEAD_REQUIRED"
    assert rt.execute(replace(req, evidence_ref=None)).reason == "HOLD_MISSING_TEST_OR_VERIFICATION_EVIDENCE"


def test_sofia_repository_write_requires_scoped_authority_and_merge_path_stays_external():
    rt = runtime("SOFIA")
    req = base_request("SOFIA")
    denied = rt.execute(replace(req, external_write_requested=True, authority_ref=None))
    assert denied.status is DecisionStatus.DENIED
    assert denied.mutation_count == 0
    assert rt.execute(replace(req, promotion_requested=True)).reason == "CANONICAL_PROMOTION_NOT_AUTHORIZED"


def test_metis_preserves_provenance_uncertainty_and_strategy_authority_boundary():
    rt = runtime("METIS")
    req = base_request("METIS")
    assert rt.execute(replace(req, provenance_ref=None)).reason == "HOLD_SOURCE_PROVENANCE_REQUIRED"
    denied = rt.execute(replace(req, strategy_as_execution_authority=True))
    assert denied.reason == "STRATEGY_TO_EXECUTION_AUTHORITY_FORBIDDEN"
    stale = replace(req, evidence_state=EvidenceState.STALE, mutation={next(iter(req.mutation)): "x", "certainty": "CERTAIN"})
    receipt = rt.execute(stale)
    assert receipt.status is DecisionStatus.HOLD
    assert receipt.mutation_count == 0


def test_auri_preserves_v04_provenance_reservation_and_registry_promotion_separation():
    rt = runtime("AURI")
    req = base_request("AURI")
    assert "AURI_V04_PROVENANCE_RESERVATION_OPEN" in PROFILES["AURI"].preserved_reservations
    denied = rt.execute(replace(req, historical_provenance_claimed_resolved=True))
    assert denied.reason == "HISTORICAL_V04_PROVENANCE_NOT_CURRENT_PROOF"
    assert denied.mutation_count == 0
    assert rt.execute(replace(req, promotion_requested=True)).reason == "CANONICAL_PROMOTION_NOT_AUTHORIZED"


def test_synergeia_requires_channel_authority_and_package_return_identity():
    rt = runtime("SYNERGEIA")
    req = base_request("SYNERGEIA")
    denied = rt.execute(replace(req, external_write_requested=True, authority_ref=None))
    assert denied.reason == "EXTERNAL_CHANNEL_AUTHORITY_REQUIRED"
    hold = rt.execute(replace(req, package_id=None))
    assert hold.status is DecisionStatus.HOLD
    mismatch = rt.execute(replace(req, return_receipt_package_id="package:other"))
    assert mismatch.reason == "RETURN_RECEIPT_PACKAGE_MISMATCH"


def test_lyra_corrected_csp_identity_ownership_and_authority_separation():
    rt = runtime("LYRA")
    req = base_request("LYRA")
    assert "CSP_LYRA_VNEXT_CORR_001_PRECEDENCE" in PROFILES["LYRA"].deterministic_policies
    assert rt.execute(replace(req, superseded_specialty_requested=True)).reason == "SUPERSEDED_SPECIALTY_REVERSION_FORBIDDEN"
    assert rt.execute(replace(req, communication_as_institutional_authority=True)).reason == "COMMUNICATION_OUTPUT_NOT_INSTITUTIONAL_AUTHORITY"
    assert rt.execute(replace(req, authority_ref="IMPLICIT_BRAND_OWNERSHIP_TRANSFER")).reason == "IMPLICIT_BRAND_OWNERSHIP_TRANSFER_FORBIDDEN"


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_valid_first_governor_write_is_local_and_receipted(ocs):
    rt = runtime(ocs)
    receipt = rt.execute(base_request(ocs))
    assert receipt.status is DecisionStatus.ACCEPTED
    assert receipt.mutation_count == 1
    assert receipt.state_version_before == 0
    assert receipt.state_version_after == 1
    assert receipt.identity_ref == PROFILES[ocs].identity_ref
    assert receipt.derivation_ref == PROFILES[ocs].derivation_ref
