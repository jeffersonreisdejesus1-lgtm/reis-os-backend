from __future__ import annotations

import pytest

from app.noesis_r7.contracts import GovernorContract, GovernorFunction, R7InvariantError
from app.noesis_r7.integration import R7ArchitecturalReadiness
from app.noesis_r7.physiology_bindings import BINDING_REFS, materialized_integration_contract
from app.noesis_r7.roster import DERIVATION_REF, DERIVED_GOVERNOR_ROSTER, assert_derived_governor
from app.noesis_r7.runtime import R7GovernanceRuntime


def _ready() -> R7ArchitecturalReadiness:
    return R7ArchitecturalReadiness(
        r7_i_taxonomy_frozen=True,
        r7_o_taxonomy_frozen=True,
        cross_taxonomy_complete=True,
        normalized_requirements_available=True,
        governor_derivation_valid=True,
        derivation_ref=DERIVATION_REF,
    )


def _contract(governor_id: str, state_key: str) -> GovernorContract:
    return GovernorContract(
        governor_id=governor_id,
        function=GovernorFunction.STATE,
        owned_state_keys=(state_key,),
        readable_state_keys=(state_key,),
        allowed_commands=("UPDATE_STATE",),
        authority_ceiling_ref="AUTH::R7::TEST",
    )


def test_derived_roster_is_exactly_17_unique_governors() -> None:
    assert len(DERIVED_GOVERNOR_ROSTER) == 17
    assert len({item.governor_id for item in DERIVED_GOVERNOR_ROSTER}) == 17
    assert sum(item.domain.value == "R7-I" for item in DERIVED_GOVERNOR_ROSTER) == 10
    assert sum(item.domain.value == "R7-O" for item in DERIVED_GOVERNOR_ROSTER) == 7


def test_roster_rejects_non_derived_governor() -> None:
    assert_derived_governor("A-CTX", derivation_ref=DERIVATION_REF)
    with pytest.raises(R7InvariantError, match="R7_GOVERNOR_NOT_IN_DERIVED_ROSTER"):
        assert_derived_governor("A-EXEC", derivation_ref=DERIVATION_REF)


def test_runtime_direct_registration_cannot_bypass_derived_roster() -> None:
    runtime = R7GovernanceRuntime(
        mission_id="R7-ROSTER-BYPASS-TEST",
        integration=materialized_integration_contract(),
        architectural_readiness=_ready(),
    )
    with pytest.raises(R7InvariantError, match="R7_GOVERNOR_NOT_IN_DERIVED_ROSTER"):
        runtime.register_governor(_contract("A-EXEC", "exec.state"))
    assert runtime.state == {}


def test_runtime_direct_registration_accepts_derived_governor_only() -> None:
    runtime = R7GovernanceRuntime(
        mission_id="R7-DERIVED-REGISTER-TEST",
        integration=materialized_integration_contract(),
        architectural_readiness=_ready(),
    )
    runtime.register_governor(_contract("A-CTX", "ctx.state"))
    assert runtime.current_generation("A-CTX") == 1


def test_six_r1_r6_bindings_are_materialized_as_distinct_refs() -> None:
    contract = materialized_integration_contract()
    contract.assert_complete_r7_integration()
    assert contract.full_r7_integration_proven is True
    assert len(BINDING_REFS) == 6
    assert len(set(BINDING_REFS.values())) == 6


def test_architectural_readiness_requires_derivation_reference() -> None:
    readiness = _ready()
    assert readiness.governor_activation_allowed is True
