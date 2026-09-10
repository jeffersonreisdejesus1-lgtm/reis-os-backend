import pytest

from ocs_operationalization import (
    OCS_RUNTIME_BINDINGS,
    assert_operationalization_invariants,
    get_binding,
)


def test_all_ten_ocs_are_bound():
    assert set(OCS_RUNTIME_BINDINGS) == {
        "NOESIS", "DEDALA", "SYNESIS", "SOFIA", "IRIS",
        "LYRA", "AGORA", "AURI", "METIS", "SYNERGEIA",
    }


def test_global_invariants_hold():
    assert_operationalization_invariants()


@pytest.mark.parametrize("ocs_id", OCS_RUNTIME_BINDINGS.keys())
def test_no_ocs_gets_production_or_authority_expansion(ocs_id):
    binding = get_binding(ocs_id)
    assert binding.production_effects is False
    assert binding.authority_expansion is False
    assert "PRODUCTION_EFFECT" in binding.forbidden_runtime_capabilities
    assert "AUTHORITY_EXPANSION" in binding.forbidden_runtime_capabilities
    assert "SELF_PROMOTE" in binding.forbidden_runtime_capabilities
    assert "FOUNDER_GATE_BYPASS" in binding.forbidden_runtime_capabilities


def test_unknown_ocs_fails_closed():
    with pytest.raises(KeyError, match="UNKNOWN_OCS"):
        get_binding("UNKNOWN")
