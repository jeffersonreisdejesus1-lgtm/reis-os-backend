from dataclasses import replace
from copy import deepcopy

import pytest

from app.ocs_v1_batch import (
    DecisionStatus,
    EvidenceState,
    GovernanceRequest,
    OCSV1InvariantError,
    OCSV1Runtime,
    PROFILES,
)


BOUND_OBJECT = "object:1"
BOUND_HEAD = "0123456789abcdef"


def runtime(ocs: str) -> OCSV1Runtime:
    profile = PROFILES[ocs]
    kwargs = {}
    if ocs in {"AGORA", "SOFIA"}:
        kwargs = {"bound_object_ref": BOUND_OBJECT, "bound_exact_head": BOUND_HEAD}
    return OCSV1Runtime(
        profile=profile,
        binding_refs=dict(profile.binding_refs),
        derivation_ref=profile.derivation_ref,
        **kwargs,
    )


def base_request(ocs: str, governor_index: int = 0) -> GovernanceRequest:
    profile = PROFILES[ocs]
    governor = profile.governors[governor_index]
    kwargs = dict(
        request_id=f"req:{ocs}:1",
        ocs_id=ocs,
        governor_id=governor.governor_id,
        operation=governor.allowed_operations[0],
        namespace=governor.writable_namespaces[0],
        mutation={governor.owned_state_keys[0]: "ok"},
        expected_state_version=0,
        expected_generation=0,
        evidence_state=EvidenceState.CURRENT,
        evidence_ref="evidence:1",
        provenance_ref="provenance:1",
        object_ref=BOUND_OBJECT,
        exact_head=BOUND_HEAD,
        authority_ref="AUTHORITY:SCOPED",
        package_id="package:1",
        specialty_ref="CSP-LYRA-vNEXT-CORR-001",
        causal_consistent=True,
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
    kwargs = {}
    if ocs in {"AGORA", "SOFIA"}:
        kwargs = {"bound_object_ref": BOUND_OBJECT, "bound_exact_head": BOUND_HEAD}
    with pytest.raises(OCSV1InvariantError, match="DERIVATION_REF_MISMATCH"):
        OCSV1Runtime(profile=profile, binding_refs=dict(profile.binding_refs), derivation_ref="NOESIS-ROSTER", **kwargs)
    bad = dict(profile.binding_refs)
    bad["R6_R7_BINDING_REF"] = "wrong"
    with pytest.raises(OCSV1InvariantError, match="R1_R6_BINDING_REF_MISMATCH"):
        OCSV1Runtime(profile=profile, binding_refs=bad, derivation_ref=profile.derivation_ref, **kwargs)


@pytest.mark.parametrize("ocs", ["AGORA", "SOFIA"])
def test_exact_object_head_binding_required_at_construction(ocs):
    profile = PROFILES[ocs]
    with pytest.raises(OCSV1InvariantError, match="EXACT_OBJECT_HEAD_BINDING_REQUIRED"):
        OCSV1Runtime(profile=profile, binding_refs=dict(profile.binding_refs), derivation_ref=profile.derivation_ref)


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_cross_ocs_and_cross_owner_writes_deny_zero_mutation(ocs):
    rt = runtime(ocs)
    request = base_request(ocs)
    cross = replace(request, ocs_id="NOESIS")
    receipt = rt.execute(cross)
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.mutation_count == 0
    assert rt.state_version == 0

    receipt = rt.execute(replace(request, mutation={"foreign_key": "x"}))
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


def test_dedala_requires_evidence_provenance_and_causal_consistency():
    rt = runtime("DEDALA")
    req = base_request("DEDALA")
    assert rt.execute(replace(req, evidence_ref=None)).reason == "HOLD_EVIDENCE_PROVENANCE_REQUIRED"
    assert rt.execute(replace(req, provenance_ref=None)).reason == "HOLD_EVIDENCE_PROVENANCE_REQUIRED"
    causal = rt.execute(replace(req, causal_consistent=False))
    assert causal.status is DecisionStatus.HOLD
    assert causal.reason == "HOLD_CAUSAL_INCONSISTENCY"
    accepted = rt.execute(req)
    assert accepted.status is DecisionStatus.ACCEPTED
    assert accepted.mutation_count == 1


def test_agora_requires_exact_bound_object_head_and_missing_evidence_never_passes():
    rt = runtime("AGORA")
    req = base_request("AGORA")
    assert rt.execute(replace(req, exact_head="wrong")).reason == "HOLD_EXACT_IMPLEMENTATION_OBJECT_HEAD_MISMATCH"
    assert rt.execute(replace(req, object_ref="wrong")).reason == "HOLD_EXACT_IMPLEMENTATION_OBJECT_HEAD_MISMATCH"
    assert rt.execute(replace(req, evidence_ref=None)).reason == "HOLD_MISSING_TEST_OR_VERIFICATION_EVIDENCE"


def test_sofia_repository_write_requires_scoped_authority_and_exact_binding():
    rt = runtime("SOFIA")
    req = base_request("SOFIA")
    assert rt.execute(replace(req, exact_head="wrong")).reason == "HOLD_EXACT_REPOSITORY_OBJECT_HEAD_MISMATCH"
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
    stale = replace(req, evidence_state=EvidenceState.STALE)
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


def test_synergeia_requires_channel_authority_package_and_return_receipt_binding():
    rt = runtime("SYNERGEIA")
    req = base_request("SYNERGEIA")
    denied = rt.execute(replace(req, external_write_requested=True, authority_ref=None))
    assert denied.reason == "EXTERNAL_CHANNEL_AUTHORITY_REQUIRED"
    hold = rt.execute(replace(req, package_id=None))
    assert hold.status is DecisionStatus.HOLD

    delivery = base_request("SYNERGEIA", governor_index=3)
    missing_return = rt.execute(delivery)
    assert missing_return.status is DecisionStatus.HOLD
    assert missing_return.reason == "HOLD_RETURN_RECEIPT_REQUIRED"
    mismatch = rt.execute(replace(delivery, return_receipt_package_id="package:other"))
    assert mismatch.reason == "RETURN_RECEIPT_PACKAGE_MISMATCH"
    accepted = rt.execute(replace(delivery, return_receipt_package_id="package:1"))
    assert accepted.status is DecisionStatus.ACCEPTED


def test_lyra_corrected_csp_identity_ownership_and_authority_separation():
    rt = runtime("LYRA")
    req = base_request("LYRA")
    assert "CSP_LYRA_VNEXT_CORR_001_PRECEDENCE" in PROFILES["LYRA"].deterministic_policies
    assert rt.execute(replace(req, specialty_ref="OLD-CSP")).reason == "CORRECTED_CSP_PRECEDENCE_REQUIRED"
    assert rt.execute(replace(req, superseded_specialty_requested=True)).reason == "SUPERSEDED_SPECIALTY_REVERSION_FORBIDDEN"
    assert rt.execute(replace(req, communication_as_institutional_authority=True)).reason == "COMMUNICATION_OUTPUT_NOT_INSTITUTIONAL_AUTHORITY"
    assert rt.execute(replace(req, authority_ref="IMPLICIT_BRAND_OWNERSHIP_TRANSFER")).reason == "IMPLICIT_BRAND_OWNERSHIP_TRANSFER_FORBIDDEN"


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_generation_fencing_denies_stale_writer_zero_mutation(ocs):
    rt = runtime(ocs)
    req = base_request(ocs)
    rt.fence_generation(req.governor_id)
    receipt = rt.execute(req)
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.reason == "STALE_GOVERNOR_GENERATION"
    assert receipt.mutation_count == 0
    assert rt.state_version == 0


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_recovery_requires_exact_identity_roster_generation_namespaces_and_reservations(ocs):
    rt = runtime(ocs)
    snapshot = rt.snapshot()

    bad_identity = deepcopy(snapshot)
    bad_identity["identity_ref"] = "other"
    with pytest.raises(OCSV1InvariantError, match="RECOVERY_IDENTITY_MISMATCH"):
        rt.restore_snapshot(bad_identity)

    omitted_governor = deepcopy(snapshot)
    omitted_governor["governor_ids"] = omitted_governor["governor_ids"][:-1]
    with pytest.raises(OCSV1InvariantError, match="RECOVERY_GOVERNOR_ROSTER_MISMATCH"):
        rt.restore_snapshot(omitted_governor)

    omitted_generation = deepcopy(snapshot)
    omitted_generation["generation"].pop(next(iter(omitted_generation["generation"])))
    with pytest.raises(OCSV1InvariantError, match="RECOVERY_GENERATION_OWNER_MISMATCH"):
        rt.restore_snapshot(omitted_generation)

    omitted_namespace = deepcopy(snapshot)
    omitted_namespace["state"].pop(next(iter(omitted_namespace["state"])))
    with pytest.raises(OCSV1InvariantError, match="RECOVERY_NAMESPACE_MISMATCH"):
        rt.restore_snapshot(omitted_namespace)

    changed_reservation = deepcopy(snapshot)
    changed_reservation["preserved_reservations"] = []
    if PROFILES[ocs].preserved_reservations:
        with pytest.raises(OCSV1InvariantError, match="RECOVERY_RESERVATION_MISMATCH"):
            rt.restore_snapshot(changed_reservation)


@pytest.mark.parametrize("ocs", ["AGORA", "SOFIA"])
def test_recovery_rejects_object_head_binding_drift(ocs):
    rt = runtime(ocs)
    snapshot = rt.snapshot()
    snapshot["bound_exact_head"] = "wrong"
    with pytest.raises(OCSV1InvariantError, match="RECOVERY_OBJECT_HEAD_BINDING_MISMATCH"):
        rt.restore_snapshot(snapshot)


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
