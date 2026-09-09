from copy import deepcopy
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


def base_request(ocs: str) -> GovernanceRequest:
    governor = PROFILES[ocs].governors[0]
    return GovernanceRequest(
        request_id=f"repair:{ocs}:1",
        ocs_id=ocs,
        governor_id=governor.governor_id,
        operation=governor.allowed_operations[0],
        namespace=governor.writable_namespaces[0],
        mutation={governor.owned_state_keys[0]: "ok"},
        expected_state_version=0,
        expected_generation=0,
        evidence_state=EvidenceState.CURRENT,
        evidence_ref="evidence:repair",
        provenance_ref="provenance:repair",
        object_ref=BOUND_OBJECT,
        exact_head=BOUND_HEAD,
        authority_ref="AUTHORITY:SCOPED",
        package_id="package:repair",
        specialty_ref="CSP-LYRA-vNEXT-CORR-001",
        causal_consistent=True,
    )


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_recovery_rejects_foreign_unowned_key_injection(ocs):
    rt = runtime(ocs)
    snapshot = rt.snapshot()
    governor = PROFILES[ocs].governors[0]
    namespace = governor.writable_namespaces[0]
    snapshot["state"][namespace]["foreign_unowned_key"] = "injected"

    with pytest.raises(OCSV1InvariantError, match="RECOVERY_STATE_KEY_OWNERSHIP_VIOLATION"):
        rt.restore_snapshot(snapshot)

    assert rt.state_version == 0


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_recovery_rejects_key_placed_in_wrong_owner_namespace(ocs):
    rt = runtime(ocs)
    snapshot = rt.snapshot()
    governor = PROFILES[ocs].governors[0]
    owned_key = governor.owned_state_keys[0]
    wrong_namespace = next(
        namespace for namespace in PROFILES[ocs].namespaces
        if namespace not in governor.writable_namespaces
    )
    snapshot["state"][wrong_namespace][owned_key] = "wrong-owner-placement"

    with pytest.raises(OCSV1InvariantError, match="RECOVERY_STATE_KEY_OWNERSHIP_VIOLATION"):
        rt.restore_snapshot(snapshot)

    assert rt.state_version == 0


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_successful_restore_fences_pre_recovery_writer(ocs):
    rt = runtime(ocs)
    pre_recovery_request = base_request(ocs)
    snapshot = deepcopy(rt.snapshot())

    rt.restore_snapshot(snapshot)

    receipt = rt.execute(pre_recovery_request)
    assert receipt.status is DecisionStatus.DENIED
    assert receipt.reason == "STALE_GOVERNOR_GENERATION"
    assert receipt.mutation_count == 0
    assert rt.state_version == 0


@pytest.mark.parametrize("ocs", sorted(PROFILES))
def test_post_recovery_generation_writer_succeeds(ocs):
    rt = runtime(ocs)
    snapshot = deepcopy(rt.snapshot())
    rt.restore_snapshot(snapshot)

    request = base_request(ocs)
    request = replace(
        request,
        expected_generation=rt.generation[request.governor_id],
        expected_state_version=rt.state_version,
    )
    receipt = rt.execute(request)

    assert receipt.status is DecisionStatus.ACCEPTED
    assert receipt.mutation_count == 1
    assert receipt.state_version_after == 1
