import pytest

from app.cupuwa_multi_ocs.contracts import (
    ContractViolation,
    ImplementationContract,
    MissionContract,
    ReconciliationResult,
    ReconciliationState,
    SpecialistHandoff,
)

HEAD = "5c2deee6a9b04c4d686e17cf16dff3b0e3d61c5c"
AUTHORITY = "authority://sofia/current"


def mission(**changes: object) -> MissionContract:
    values: dict[str, object] = {
        "mission_id": "CUPUWA-MULTI-OCS-SLICE-001",
        "product": "CUPUWA",
        "increment_id": "SLICE-001",
        "bound_object": "cupuwa/mvp-build",
        "bound_head": HEAD,
        "requested_outcome": "contract substrate",
        "constraints": ("authority-neutral",),
        "authority_ref": AUTHORITY,
        "required_capabilities": ("code",),
        "evidence_policy": "NO_EVIDENCE->NO_CLAIM",
        "completion_policy": "qualified-only",
    }
    values.update(changes)
    return MissionContract(**values)  # type: ignore[arg-type]


def handoff(**changes: object) -> SpecialistHandoff:
    values: dict[str, object] = {
        "mission_id": "CUPUWA-MULTI-OCS-SLICE-001",
        "source_ocs": "NÓESIS",
        "target_ocs": "SOFIA",
        "bound_object": "cupuwa/mvp-build",
        "bound_head": HEAD,
        "scope": ("contracts",),
        "inputs": ("plan-001",),
        "expected_outputs": ("contract-substrate",),
        "authority_envelope_ref": AUTHORITY,
        "required_capabilities": ("code",),
        "tool_permissions": (),
        "evidence_requirements": ("tests",),
        "completion_criteria": ("fail-closed",),
        "failure_state": "HOLD",
    }
    values.update(changes)
    return SpecialistHandoff(**values)  # type: ignore[arg-type]


def reconciliation(state: ReconciliationState) -> ReconciliationResult:
    return ReconciliationResult(
        mission_id="CUPUWA-MULTI-OCS-SLICE-001",
        bound_head=HEAD,
        state=state,
        accepted_receipts=(
            ("receipt-1",) if state is ReconciliationState.CONSISTENT else ()
        ),
    )


def implementation(
    state: ReconciliationState,
    findings: tuple[str, ...] = (),
) -> ImplementationContract:
    return ImplementationContract(
        mission_id="CUPUWA-MULTI-OCS-SLICE-001",
        bound_head=HEAD,
        accepted_decisions=("decision-1",),
        decision_evidence_refs=("evidence-1",),
        unresolved_findings=findings,
        implementation_scope=("contracts",),
        required_effect_capabilities=("code",),
        authority_envelope_ref=AUTHORITY,
        lease_requirements=("per-action",),
        required_tests=("contract-invariants",),
        evidence_requirements=("pytest",),
        reconciliation=reconciliation(state),
    )


def test_missing_required_fields_fail_closed() -> None:
    with pytest.raises(ContractViolation, match="mission_id_required"):
        mission(mission_id="")
    with pytest.raises(ContractViolation, match="bound_head_required"):
        mission(bound_head="")
    with pytest.raises(ContractViolation, match="authority_ref_required"):
        mission(authority_ref="")


def test_mission_identity_cannot_silently_change_across_handoff() -> None:
    with pytest.raises(ContractViolation, match="mission_identity_drift"):
        handoff(mission_id="other").validate_against(mission())


def test_bound_head_cannot_silently_change_across_handoff() -> None:
    with pytest.raises(ContractViolation, match="bound_head_drift"):
        handoff(bound_head="other-head").validate_against(mission())


def test_authority_transfer_is_rejected() -> None:
    with pytest.raises(ContractViolation, match="authority_transfer_prohibited"):
        handoff(authority_transfer=True)


def test_memory_import_is_rejected() -> None:
    with pytest.raises(ContractViolation, match="cross_ocs_memory_import_prohibited"):
        handoff(memory_import=True)


def test_contract_layer_material_effect_claim_is_rejected() -> None:
    with pytest.raises(
        ContractViolation,
        match="handoff_material_effect_claim_prohibited",
    ):
        handoff(material_effect_claim=True)


def test_invalid_reconciliation_state_is_rejected() -> None:
    with pytest.raises(ContractViolation, match="invalid_reconciliation_state"):
        ReconciliationResult(
            mission_id="m",
            bound_head=HEAD,
            state="PASS",  # type: ignore[arg-type]
            accepted_receipts=(),
        )


@pytest.mark.parametrize(
    "state",
    [
        ReconciliationState.CONFLICT,
        ReconciliationState.UNKNOWN,
        ReconciliationState.INSUFFICIENT_EVIDENCE,
        ReconciliationState.HOLD,
    ],
)
def test_non_consistent_reconciliation_cannot_execute(
    state: ReconciliationState,
) -> None:
    assert implementation(state).execution_allowed is False


def test_unresolved_findings_prevent_execution() -> None:
    assert (
        implementation(
            ReconciliationState.CONSISTENT,
            ("open-finding",),
        ).execution_allowed
        is False
    )


def test_consistent_reconciliation_is_contract_ready_not_material_effect() -> None:
    contract = implementation(ReconciliationState.CONSISTENT)
    assert contract.execution_allowed is True
    assert not hasattr(contract, "effector")
    assert not hasattr(contract, "tool_permissions")


def test_canonical_registry_still_prohibits_direct_effect_routes() -> None:
    from app.profile_bindings.canonical_registry import (
        CANONICAL_OCS_REGISTRY,
        validate_canonical_registry,
    )

    validate_canonical_registry()
    assert len(CANONICAL_OCS_REGISTRY) == 72
    assert all(
        profile.capability_adapters == ()
        for profile in CANONICAL_OCS_REGISTRY.values()
    )
    assert all(
        profile.tool_permissions == ()
        for profile in CANONICAL_OCS_REGISTRY.values()
    )
