from app.cupuwa_multi_ocs.p0_coi_ingress import discover_and_compose

def test_p0_coi_ingress_is_fail_closed_and_bound_to_72_registry():
    result = discover_and_compose()
    assert result["pool_size"] == 72
    assert result["mission_id"] == "CUPUWA-P0-CORE-FINANCE-MATERIAL-001"
    assert result["authority_granted"] is False
    assert result["effects_permitted"] is False
    assert result["missing_capabilities"] == []
    assert result["status"] == "COMPOSED"
    assert result["discovery_receipt"]
    assert result["composition_receipt"]
    selected = set(result["selected_ocs"])
    for expected in {"NOMÍSMA", "KOTLIN", "MNÉME", "ÍRIS", "MONÁDA", "TELOS", "PIPELINE", "MIKRÓN"}:
        assert expected in selected
