from __future__ import annotations

from typing import Any


METRIC_SOURCE_REF = "command-b10://cupuwa-ocs-ai"
MEASUREMENT_VERSION = "b10-metrics-v1"


def _metric(metric_id: str, *, kind: str, target: Any = None, target_max: Any = None) -> dict[str, Any]:
    return {
        "id": metric_id,
        "kind": kind,
        "target": target,
        "target_max": target_max,
        "source_ref": METRIC_SOURCE_REF,
        "measurement_method": "event_or_projection_derived",
        "measurement_version": MEASUREMENT_VERSION,
        "observed_at": None,
        "window": None,
        "completeness": "UNKNOWN",
        "unknown_semantics": "UNKNOWN_IS_NOT_ZERO_OR_PASS",
        "can_promote": False,
        "can_close_quality_gate_alone": False,
    }


METRIC_SPECS: tuple[dict[str, Any], ...] = (
    _metric("ouro_available_when_prata_unavailable_rate", target=1.0, kind="ratio"),
    _metric("prata_failure_causing_ouro_failure", target=0, kind="count"),
    _metric("routing_loop_count", target=0, kind="count"),
    _metric("routing_hops_p95", target_max=2, kind="count"),
    _metric("direct_inference_state_write_count", target=0, kind="count"),
    _metric("authority_bypass_count", target=0, kind="count"),
    _metric("self_promotion_count", target=0, kind="count"),
    _metric("material_action_without_receipt_count", target=0, kind="count"),
    _metric("responses_with_mode_label_rate", target=1.0, kind="ratio"),
    _metric("source_access_model_invocation_conflation_count", target=0, kind="count"),
    _metric("live_model_invocation_without_adapter_receipt_count", target=0, kind="count"),
)


def cupuwa_inspired_module_contract() -> dict[str, Any]:
    return {
        "module_id": "COMMAND_CUPUWA_INSPIRED",
        "status": "implementation_candidate",
        "principle": {
            "simple_surface": True,
            "deep_competence": True,
            "one_hand_friendly": True,
            "modest_device_compatibility": True,
            "high_reliability": True,
        },
        "ouro": {
            "role": "deterministic_operational_core",
            "depends_on_prata": False,
            "owns_inference": False,
            "direct_inference_state_write": False,
            "surfaces": [
                "facts",
                "state",
                "evidence",
                "history_lineage",
                "system_health",
                "recovery_readback",
            ],
        },
        "prata": {
            "role": "optional_intelligence_augmentation",
            "failure_must_not_break_ouro": True,
            "capabilities": [
                "general_ai",
                "ocs_specialist_inference",
                "cross_ocs_routing",
                "tool_assisted_retrieval",
                "recommendations",
                "automation_preparation",
                "provider_model_invocation_when_materially_available",
            ],
            "canonical_state_write": False,
            "self_grants_authority": False,
        },
        "shared_inference_fabric": {
            "one_engine_per_ocs": False,
            "shared_generic_engine": True,
            "model_is_ocs": False,
            "max_routing_hops": 2,
            "same_request_same_ocs_reentry": "prohibited",
            "response_modes": [
                "GENERAL_AI",
                "OCS_SPECIALIST",
                "ROUTED_OCS",
                "TOOL_ASSISTED",
                "AUTHORITY_GATED",
                "HOLD",
            ],
        },
        "metrics": [dict(item) for item in METRIC_SPECS],
        "metric_policy": {
            "no_single_metric_can_promote": True,
            "no_single_metric_can_close_quality_gate": True,
            "no_metric_can_override_evidence": True,
            "no_metric_can_suppress_required_escalation": True,
        },
        "epistemic_boundary": {
            "input_is_inference": False,
            "inference_is_command": False,
            "command_is_state": False,
            "high_confidence_is_high_authority": False,
            "unknown_is_zero": False,
            "prata_failure_is_ouro_failure": False,
        },
    }
