from dataclasses import replace

import pytest

from app.iris_v1 import (
    DecisionStatus,
    EvidenceFreshness,
    GovernorLease,
    GovernanceRequest,
    IRIS_DERIVATION_REF,
    IrisV1Bindings,
    IrisV1InvariantError,
    IrisV1Runtime,
    derived_governor_specs,
)

MISSION = "REIS-OS-OCS-REFACTOR-V1-IRIS-001"


def runtime():
    rt = IrisV1Runtime(
        mission_id=MISSION,
        bindings=IrisV1Bindings.materialized(),
        derivation_ref=IRIS_DERIVATION_REF,
    )
    for spec in derived_governor_specs():
        rt.register_governor(spec)
    rt.bind_lease(
        GovernorLease(
            lease_id="lease:iris:1",
            mission_id=MISSION,
            governor_id="GOV-IRIS-01",
            scope=("NS_IRIS_DESIGN_WORKING",),
            generation=1,
            valid_from=100.0,
            expires_at=500.0,
        )
    )
    return rt


def request(**changes):
    base = GovernanceRequest(
        request_id="req:1",
        mission_id=MISSION,
        governor_id="GOV-IRIS-01",
        operation="SET_PERCEPTION_INTERACTION_STATE",
        namespace="NS_IRIS_DESIGN_WORKING",
        mutation={"hierarchy": "clear"},
        expected_state_version=0,
        lease_id="lease:iris:1",
        generation=1,
        idempotency_key="idem:1",
        evidence_freshness=EvidenceFreshness.CURRENT,
    )
    return replace(base, **changes)


def test_runtime_construction_requires_all_six_bindings():
    refs = dict(IrisV1Bindings.materialized().refs)
    refs["R6_R7_BINDING_REF"] = ""
    with pytest.raises(IrisV1InvariantError, match="BINDINGS_INCOMPLETE"):
        IrisV1Runtime(mission_id=MISSION, bindings=IrisV1Bindings(refs), derivation_ref=IRIS_DERIVATION_REF)


def test_runtime_rejects_noncanonical_binding_identity():
    refs = dict(IrisV1Bindings.materialized().refs)
    refs["R4_R7_BINDING_REF"] = "fake:R4"
    with pytest.raises(IrisV1InvariantError, match="BINDING_REF_MISMATCH"):
        IrisV1Runtime(mission_id=MISSION, bindings=IrisV1Bindings(refs), derivation_ref=IRIS_DERIVATION_REF)


def test_wrong_derivation_ref_fails_closed():
    with pytest.raises(IrisV1InvariantError, match="DERIVATION_REF_MISMATCH"):
        IrisV1Runtime(mission_id=MISSION, bindings=IrisV1Bindings.materialized(), derivation_ref="NOESIS-R7-GOVERNOR-ROSTER-DERIVATION-001")


def test_local_roster_is_exactly_four_and_noesis_id_is_rejected():
    specs = derived_governor_specs()
    assert {spec.governor_id for spec in specs} == {"GOV-IRIS-01", "GOV-IRIS-02", "GOV-IRIS-03", "GOV-IRIS-04"}
    rt = runtime()
    with pytest.raises(IrisV1InvariantError, match="GOVERNOR_NOT_DERIVED"):
        rt.fence_generation("A-CTX")


def test_governor_contract_substitution_is_rejected():
    rt = IrisV1Runtime(mission_id=MISSION, bindings=IrisV1Bindings.materialized(), derivation_ref=IRIS_DERIVATION_REF)
    forged = replace(derived_governor_specs()[0], role="AUTHORITY_ROOT")
    with pytest.raises(IrisV1InvariantError, match="CONTRACT_NOT_CANONICAL"):
        rt.register_governor(forged)


def test_accessibility_conflict_forces_hold_and_zero_mutation():
    rt = runtime()
    receipt = rt.execute(request(accessibility_conflict=True), now=110.0)
    assert receipt.status is DecisionStatus.HOLD
    assert receipt.reason == "HOLD_ACCESSIBILITY_CONFLICT"
    assert receipt.mutation_count == 0
    assert rt.state_version == 0


@pytest.mark.parametrize("freshness", [EvidenceFreshness.STALE, EvidenceFreshness.UNKNOWN, EvidenceFreshness.CONFLICTED])
def test_non_current_evidence_cannot_support_current_mutation(freshness):
    rt = runtime()
    receipt = rt.execute(request(evidence_freshness=freshness), now=110.0)
    assert receipt.status is DecisionStatus.HOLD
    assert receipt.mutation_count == 0


def test_cross_owner_and_institutional_state_write_are_denied():
    rt = runtime()
    receipt = rt.execute(request(namespace="NS_IRIS_INSTITUTIONAL", mutation={"identity": "forged"}), now=110.0)
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.mutation_count == 0
    assert rt.identity_state_root == "EC-IRIS-GENERALIST-EVO-001 + IRIS_STATE.json"


def test_state_key_owner_is_fail_closed():
    rt = runtime()
    receipt = rt.execute(request(mutation={"route": "DEDALA"}), now=110.0)
    assert receipt.reason == "STATE_KEY_OWNERSHIP_VIOLATION"
    assert receipt.mutation_count == 0


def test_operation_is_governor_scoped():
    rt = runtime()
    receipt = rt.execute(request(operation="SET_DESIGN_ROUTING_STATE"), now=110.0)
    assert receipt.reason == "OPERATION_NOT_ALLOWED_FOR_GOVERNOR"
    assert receipt.mutation_count == 0


def test_engineering_cannot_claim_design_approval_or_transfer_authority():
    rt = runtime()
    approval = rt.execute(request(design_approval_claimed=True), now=110.0)
    transfer = rt.execute(request(authority_transfer_requested=True), now=110.0)
    assert approval.reason == "DESIGN_APPROVAL_REQUIRES_IRIS_AUTHORITY"
    assert transfer.reason == "AUTHORITY_TRANSFER_FORBIDDEN"
    assert approval.mutation_count == transfer.mutation_count == 0


def test_material_effect_is_outside_local_r7_boundary():
    rt = runtime()
    receipt = rt.execute(request(material_effect_requested=True), now=110.0)
    assert receipt.reason == "MATERIAL_EFFECT_OUTSIDE_LOCAL_R7_BOUNDARY"
    assert receipt.mutation_count == 0


def test_valid_request_commits_only_owned_local_design_working_state():
    rt = runtime()
    receipt = rt.execute(request(), now=110.0)
    assert receipt.status is DecisionStatus.ACCEPTED
    assert receipt.mutation_count == 1
    assert rt.state_version == 1
    assert rt.state["NS_IRIS_DESIGN_WORKING"]["hierarchy"] == "clear"
    assert rt.state["NS_IRIS_INSTITUTIONAL"] == {}


def test_idempotent_replay_does_not_mutate_twice_and_conflict_is_denied():
    rt = runtime()
    first = rt.execute(request(), now=110.0)
    replay = rt.execute(request(), now=110.0)
    conflict = rt.execute(request(mutation={"hierarchy": "different"}), now=110.0)
    assert first.mutation_count == 1
    assert replay.idempotent_replay is True
    assert replay.state_version_after == 1
    assert conflict.reason == "IDEMPOTENCY_KEY_CONFLICT"
    assert rt.state_version == 1


def test_expired_lease_and_fenced_generation_fail_closed():
    rt = runtime()
    expired = rt.execute(request(), now=501.0)
    assert expired.reason == "LEASE_EXPIRED_OR_NOT_YET_VALID"
    assert expired.mutation_count == 0
    assert rt.fence_generation("GOV-IRIS-01") == 2
    fenced = rt.execute(request(), now=110.0)
    assert fenced.reason == "FENCED_GENERATION"
    assert fenced.mutation_count == 0


def test_recovery_is_owner_scoped_fences_generation_and_invalidates_idempotency():
    rt = runtime()
    rt.execute(request(), now=110.0)
    cp = rt.checkpoint("cp:1", governor_id="GOV-IRIS-01")
    assert cp.owned_state == {"hierarchy": "clear"}

    rt.bind_lease(GovernorLease(
        lease_id="lease:iris:2",
        mission_id=MISSION,
        governor_id="GOV-IRIS-01",
        scope=("NS_IRIS_DESIGN_WORKING",),
        generation=1,
        valid_from=100.0,
        expires_at=500.0,
    ))
    change = request(
        request_id="req:2",
        mutation={"hierarchy": "dense"},
        expected_state_version=1,
        lease_id="lease:iris:2",
        idempotency_key="idem:2",
    )
    assert rt.execute(change, now=110.0).status is DecisionStatus.ACCEPTED
    assert rt.recover_governor("GOV-IRIS-01", checkpoint_id="cp:1") == 2
    assert rt.state["NS_IRIS_DESIGN_WORKING"]["hierarchy"] == "clear"

    replay_old = rt.execute(request(expected_state_version=3), now=110.0)
    assert replay_old.reason == "IDEMPOTENCY_KEY_INVALIDATED"


def test_stale_state_version_fails_closed_as_stale_writer_guard():
    rt = runtime()
    assert rt.execute(request(), now=110.0).status is DecisionStatus.ACCEPTED
    stale = rt.execute(request(request_id="req:stale", idempotency_key="idem:stale"), now=110.0)
    assert stale.reason == "STALE_STATE_VERSION"
    assert stale.mutation_count == 0
