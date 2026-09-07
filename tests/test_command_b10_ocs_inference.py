from app.command.cupuwa_module import cupuwa_inspired_module_contract
from app.command.ocs_inference import (
    InferencePlanRequest,
    RequestScope,
    ResponseMode,
    plan_inference,
)


def test_general_question_falls_back_without_institutional_claim() -> None:
    plan = plan_inference(InferencePlanRequest(prompt="traga um link de referência"))
    assert plan.mode is ResponseMode.GENERAL_AI
    assert plan.ocs_id is None
    assert plan.may_answer is True
    assert plan.canonical_state_write_allowed is False
    assert plan.may_execute_material_effect is False


def test_explicit_ocs_request_uses_specialist_mode() -> None:
    plan = plan_inference(
        InferencePlanRequest(prompt="analise o risco", requested_ocs="DÉDALA")
    )
    assert plan.mode is ResponseMode.OCS_SPECIALIST
    assert plan.ocs_id == "DÉDALA"
    assert plan.may_recommend is True
    assert plan.may_execute_material_effect is False


def test_specialist_scope_requires_valid_ocs() -> None:
    plan = plan_inference(
        InferencePlanRequest(
            prompt="analise",
            request_scope=RequestScope.SPECIALIST,
        )
    )
    assert plan.mode is ResponseMode.HOLD
    assert "specialist_scope_without_ocs" in plan.reasons


def test_unknown_ocs_fails_closed() -> None:
    plan = plan_inference(
        InferencePlanRequest(prompt="analise", requested_ocs="OCS-INVENTADA")
    )
    assert plan.mode is ResponseMode.HOLD
    assert "requested_ocs_unknown" in plan.reasons


def test_tool_request_requires_capability_but_does_not_fake_execution() -> None:
    plan = plan_inference(
        InferencePlanRequest(
            prompt="traga o link oficial",
            requested_ocs="NÓESIS",
            tool_required=True,
        )
    )
    assert plan.mode is ResponseMode.TOOL_ASSISTED
    assert plan.tool_capability_required is True
    assert plan.may_execute_material_effect is False
    assert plan.canonical_state_write_allowed is False


def test_material_effect_is_always_authority_gated() -> None:
    plan = plan_inference(
        InferencePlanRequest(
            prompt="promova esta missão",
            requested_ocs="NÓESIS",
            material_effect_requested=True,
        )
    )
    assert plan.mode is ResponseMode.AUTHORITY_GATED
    assert plan.authority_gate_required is True
    assert plan.may_prepare_action is True
    assert plan.may_execute_material_effect is False
    assert "authority_ref_missing" in plan.reasons


def test_same_request_same_ocs_reentry_is_prohibited() -> None:
    plan = plan_inference(
        InferencePlanRequest(
            prompt="continue",
            requested_ocs="DÉDALA",
            prior_ocs=("DÉDALA",),
        )
    )
    assert plan.mode is ResponseMode.HOLD
    assert "same_request_same_ocs_reentry_prohibited" in plan.reasons


def test_suggested_ocs_routes_once_and_tracks_hop() -> None:
    plan = plan_inference(
        InferencePlanRequest(
            prompt="avalie a interface",
            suggested_ocs="ÍRIS",
            routing_hops=0,
        )
    )
    assert plan.mode is ResponseMode.ROUTED_OCS
    assert plan.ocs_id == "ÍRIS"
    assert plan.routing_hops == 1
    assert plan.max_routing_hops == 2


def test_cupuwa_module_preserves_ouro_prata_isolation() -> None:
    module = cupuwa_inspired_module_contract()
    assert module["ouro"]["depends_on_prata"] is False
    assert module["prata"]["failure_must_not_break_ouro"] is True
    assert module["prata"]["canonical_state_write"] is False
    assert module["shared_inference_fabric"]["shared_generic_engine"] is True
    assert module["epistemic_boundary"]["prata_failure_is_ouro_failure"] is False


def test_metrics_are_non_promoting_and_unknown_is_not_pass() -> None:
    module = cupuwa_inspired_module_contract()
    assert module["metric_policy"]["no_single_metric_can_promote"] is True
    assert module["metric_policy"]["no_metric_can_override_evidence"] is True
    for metric in module["metrics"]:
        assert metric["source_ref"]
        assert metric["measurement_method"]
        assert metric["measurement_version"]
        assert metric["completeness"] == "UNKNOWN"
        assert metric["unknown_semantics"] == "UNKNOWN_IS_NOT_ZERO_OR_PASS"
        assert metric["can_promote"] is False
        assert metric["can_close_quality_gate_alone"] is False
