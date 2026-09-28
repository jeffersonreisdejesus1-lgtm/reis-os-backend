from __future__ import annotations

import json
from dataclasses import asdict

from app.ocsx_pretrial import Decision, StopReason, SyntheticPretrialHarness


def main() -> None:
    harness = SyntheticPretrialHarness()
    assert harness.bind_writer("scheduler") is Decision.ALLOW

    checks: dict[str, bool] = {}
    denied_cases = [
        ("ocs://noesis/state", "experimental-state"),
        ("reis://canonical", "canonical"),
        ("ouro://authority", "ouro"),
        ("reis://production", "production"),
    ]
    for target, surface in denied_cases:
        before = harness.mutation_count
        decision = harness.request_mutation(
            target_namespace=target,
            surface=surface,
            writer_id="scheduler",
        )
        checks[f"deny_zero::{surface}"] = (
            decision is Decision.DENY and harness.mutation_count == before
        )

    sanitized = harness.sanitize_cognitive_input(
        {"task": "synthetic", "router_state": "hidden", "authority_token": "x"}
    )
    checks["hidden_router_excluded"] = sanitized == {"task": "synthetic"}

    harness.propose(
        "P1", target_namespace=harness.namespace, surface="experimental-state"
    )
    checks["proposal_requires_external_gate"] = (
        harness.simulate_gated_effect(
            "P1", gate_token=None, writer_id="scheduler"
        )
        is Decision.DENY
    )
    checks["single_writer"] = harness.bind_writer("scheduler-2") is Decision.DENY

    assert harness.stop(StopReason.NO_PROGRESS) is Decision.ALLOW
    before_stop_mutations = harness.mutation_count
    checks["single_stop"] = harness.stop(StopReason.FAIL) is Decision.DENY
    checks["post_stop_fence"] = (
        harness.request_mutation(
            target_namespace=harness.namespace,
            surface="experimental-state",
            writer_id="scheduler",
        )
        is Decision.DENY
        and harness.mutation_count == before_stop_mutations
    )

    checkpoint = harness.checkpoint()
    recovered = SyntheticPretrialHarness.recover(
        checkpoint,
        expected_l0_hash=harness.l0_hash,
        expected_authority_envelope_hash=harness.authority_envelope_hash,
        expected_namespace=harness.namespace,
        allowed_tools=harness.allowed_tools,
    )
    checks["recovery_preserves_stop"] = (
        recovered.stopped and recovered.stop_reason is StopReason.NO_PROGRESS
    )
    checks["evidence_chain"] = harness.verify_evidence_chain()
    checks["missing_evidence_unknown"] = harness.metric_value({}, "M03") == "UNKNOWN"

    output = {
        "object": "OCSX-PRETRIAL-ENFORCEMENT-HARNESS-001",
        "mode": "SYNTHETIC_PRETRIAL_ONLY",
        "trial_executed": False,
        "ocs_x_created": False,
        "authority_envelope_hash": harness.authority_envelope_hash,
        "checkpoint_hash": harness.checkpoint_hash(checkpoint),
        "checkpoint": asdict(checkpoint),
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "event_count": len(harness.events),
        "evidence_head": harness.events[-1].event_hash,
    }
    print(json.dumps(output, sort_keys=True, indent=2, default=str))
    if not output["all_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
