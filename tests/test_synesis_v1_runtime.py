from copy import deepcopy
from dataclasses import replace

import pytest

from app.synesis_v1 import (
    AssuranceRequest,
    DecisionStatus,
    EvidenceState,
    SynesisInvariantError,
    SynesisProfile,
    SynesisV1Runtime,
)


def runtime() -> SynesisV1Runtime:
    return SynesisV1Runtime()


def request(governor_index: int = 0) -> AssuranceRequest:
    profile = SynesisProfile()
    governor = profile.governors[governor_index]
    return AssuranceRequest(
        request_id=f"synesis:req:{governor_index}:1",
        ocs_id="SYNESIS",
        governor_id=governor.governor_id,
        operation=governor.allowed_operations[0],
        namespace=governor.writable_namespaces[0],
        mutation={governor.owned_state_keys[0]: "value"},
        expected_state_version=0,
        expected_generation=0,
        object_ref="object:qualified",
        exact_revision="rev:1",
        evidence_state=EvidenceState.CURRENT,
        evidence_ref="evidence:1",
        provenance_ref="provenance:1",
        requested_disposition=DecisionStatus.PASS,
    )


def test_exact_local_roster_and_bindings():
    profile = SynesisProfile()
    profile.validate()
    assert len(profile.governors) == 4
    assert len(profile.binding_refs) == 6
    assert all(g.governor_id.startswith("GOV-SYNESIS-") for g in profile.governors)


@pytest.mark.parametrize(
    (field, reason),
    [
        ("self_assurance_requested", "SELF_ASSURANCE_FORBIDDEN"),
        ("self_homologation_requested", "SELF_HOMOLOGATION_FORBIDDEN"),
        ("promotion_requested", "CANONICAL_PROMOTION_NOT_AUTHORIZED"),
        ("runtime_activation_requested", "RUNTIME_GOVERNOR_ACTIVATION_NOT_AUTHORIZED"),
        ("authority_transfer_requested", "AUTHORITY_TRANSFER_FORBIDDEN"),
    ],
)
def test_forbidden_authority_transforms_fail_closed(field, reason):
    rt = runtime()
    receipt = rt.execute(replace(request(), **{field: True}))
    assert receipt.status is DecisionStatus.DENIED
    assert reason in receipt.reason
    assert receipt.mutation_count == 0
    assert rt.state_version == 0


def test_void_predecessor_is_rejected():
    rt = runtime()
    receipt = rt.execute(replace(request(), predecessor_ref="REF-SYNESIS-LOCAL-001"))
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.reason == "SYNESIS:VOID_PREDECESSOR_FORBIDDEN"
    assert receipt.mutation_count == 0


@pytest.mark.parametrize("state", [EvidenceState.STALE, EvidenceState.UNKNOWN, EvidenceState.CONFLICTED, EvidenceState.PARTIAL])
def test_non_current_evidence_holds_zero_mutation(state):
    rt = runtime()
    receipt = rt.execute(replace(request(), evidence_state=state))
    assert receipt.status is DecisionStatus.HOLD
    assert receipt.mutation_count == 0
    assert rt.state_version == 0


def test_missing_evidence_and_object_version_binding_hold():
    rt = runtime()
    assert rt.execute(replace(request(), object_ref=None)).status is DecisionStatus.HOLD
    rt = runtime()
    assert rt.execute(replace(request(), exact_revision=None)).status is DecisionStatus.HOLD
    rt = runtime()
    assert rt.execute(replace(request(), evidence_ref=None)).status is DecisionStatus.HOLD
    rt = runtime()
    assert rt.execute(replace(request(), provenance_ref=None)).status is DecisionStatus.HOLD


def test_cross_ocs_and_unknown_owner_writes_deny_zero_mutation():
    rt = runtime()
    cross = rt.execute(replace(request(), ocs_id="NOESIS"))
    assert cross.status is DecisionStatus.DENIED
    assert cross.mutation_count == 0

    foreign = rt.execute(replace(request(), request_id="synesis:req:foreign", mutation={"foreign_key": "x"}))
    assert foreign.status is DecisionStatus.DENIED
    assert foreign.reason == "SYNESIS:STATE_KEY_OWNERSHIP_VIOLATION"
    assert foreign.mutation_count == 0


def test_reservations_cannot_be_collapsed_to_pass():
    rt = runtime()
    receipt = rt.execute(replace(request(), reservation_refs=("ANATOMICAL_PARITY=UNPROVEN",)))
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.reason == "SYNESIS:RESERVATIONS_CANNOT_BE_COLLAPSED_TO_PASS"


def test_pass_with_reservations_requires_explicit_reservations():
    rt = runtime()
    receipt = rt.execute(replace(request(), requested_disposition=DecisionStatus.PASS_WITH_RESERVATIONS))
    assert receipt.status is DecisionStatus.HOLD

    rt = runtime()
    receipt = rt.execute(
        replace(
            request(),
            requested_disposition=DecisionStatus.PASS_WITH_RESERVATIONS,
            reservation_refs=("ANATOMICAL_PARITY=UNPROVEN",),
        )
    )
    assert receipt.status is DecisionStatus.PASS_WITH_RESERVATIONS
    assert receipt.mutation_count == 1


def test_idempotent_replay_returns_same_receipt_without_second_mutation():
    rt = runtime()
    req = request()
    first = rt.execute(req)
    second = rt.execute(req)
    assert first == second
    assert rt.state_version == 1


def test_recovery_rejects_foreign_unowned_key():
    rt = runtime()
    snap = rt.snapshot()
    namespace = SynesisProfile().governors[0].writable_namespaces[0]
    snap["state"][namespace]["foreign_key"] = "x"
    with pytest.raises(SynesisInvariantError, match="RECOVERY_STATE_KEY_OWNERSHIP_VIOLATION"):
        rt.restore_snapshot(snap)
    assert rt.state_version == 0


def test_recovery_rejects_wrong_owner_key_placement():
    rt = runtime()
    snap = rt.snapshot()
    profile = SynesisProfile()
    owned_key = profile.governors[0].owned_state_keys[0]
    wrong_namespace = profile.governors[1].writable_namespaces[0]
    snap["state"][wrong_namespace][owned_key] = "wrong"
    with pytest.raises(SynesisInvariantError, match="RECOVERY_STATE_KEY_OWNERSHIP_VIOLATION"):
        rt.restore_snapshot(snap)


def test_recovery_rejects_roster_generation_owner_and_reservation_drift():
    rt = runtime()
    snap = rt.snapshot()

    bad_roster = deepcopy(snap)
    bad_roster["governor_ids"] = bad_roster["governor_ids"][:-1]
    with pytest.raises(SynesisInvariantError, match="RECOVERY_GOVERNOR_ROSTER_MISMATCH"):
        rt.restore_snapshot(bad_roster)

    bad_generation = deepcopy(snap)
    bad_generation["generation"].pop(next(iter(bad_generation["generation"])))
    with pytest.raises(SynesisInvariantError, match="RECOVERY_GENERATION_OWNER_MISMATCH"):
        rt.restore_snapshot(bad_generation)

    bad_reservations = deepcopy(snap)
    bad_reservations["preserved_reservations"] = []
    with pytest.raises(SynesisInvariantError, match="RECOVERY_RESERVATION_MISMATCH"):
        rt.restore_snapshot(bad_reservations)


def test_pre_recovery_writer_becomes_stale_and_post_recovery_generation_succeeds():
    rt = runtime()
    stale_request = request()
    snap = rt.snapshot()
    rt.restore_snapshot(snap)

    stale = rt.execute(stale_request)
    assert stale.status is DecisionStatus.DENIED
    assert stale.reason == "SYNESIS:STALE_GOVERNOR_GENERATION"
    assert stale.mutation_count == 0

    current = replace(
        request(),
        request_id="synesis:req:post-recovery",
        expected_generation=rt.generation[request().governor_id],
        expected_state_version=rt.state_version,
    )
    accepted = rt.execute(current)
    assert accepted.status is DecisionStatus.PASS
    assert accepted.mutation_count == 1


def test_valid_local_assurance_commit_is_receipted():
    rt = runtime()
    receipt = rt.execute(request())
    assert receipt.status is DecisionStatus.PASS
    assert receipt.mutation_count == 1
    assert receipt.state_version_before == 0
    assert receipt.state_version_after == 1
