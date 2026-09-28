from dataclasses import replace

import pytest

from app.ocsx_pretrial import (
    Decision,
    GenerationStatus,
    StopReason,
    SyntheticPretrialHarness,
)


def bound_harness() -> SyntheticPretrialHarness:
    harness = SyntheticPretrialHarness()
    assert harness.bind_writer("scheduler") is Decision.ALLOW
    return harness


def test_own_namespace_synthetic_mutation_is_only_allowed_effect() -> None:
    harness = bound_harness()
    assert (
        harness.request_mutation(
            target_namespace=harness.namespace,
            surface="experimental-state",
            writer_id="scheduler",
        )
        is Decision.ALLOW
    )
    assert harness.mutation_count == 1


@pytest.mark.parametrize(
    ("target_namespace", "surface"),
    [
        ("ocs://noesis/state", "experimental-state"),
        ("reis://canonical", "canonical"),
        ("ouro://authority", "ouro"),
        ("reis://production", "production"),
    ],
)
def test_denied_surfaces_preserve_zero_mutation(
    target_namespace: str, surface: str
) -> None:
    harness = bound_harness()
    before = harness.mutation_count
    assert (
        harness.request_mutation(
            target_namespace=target_namespace,
            surface=surface,
            writer_id="scheduler",
        )
        is Decision.DENY
    )
    assert harness.mutation_count == before == 0
    assert harness.events[-1].kind == "MUTATION_DENIED"


def test_non_allowlisted_tool_is_denied_without_mutation() -> None:
    harness = bound_harness()
    assert (
        harness.request_mutation(
            target_namespace=harness.namespace,
            surface="experimental-state",
            writer_id="scheduler",
            tool="network",
        )
        is Decision.DENY
    )
    assert harness.mutation_count == 0


def test_hidden_router_and_authority_inputs_are_removed() -> None:
    harness = bound_harness()
    sanitized = harness.sanitize_cognitive_input(
        {
            "task": "synthetic",
            "router_state": "hidden",
            "internal_route": "secret",
            "ouro": "forbidden",
            "authority_token": "forbidden",
        }
    )
    assert sanitized == {"task": "synthetic"}


def test_proposal_cannot_self_authorize_effect() -> None:
    harness = bound_harness()
    harness.propose(
        "P1", target_namespace=harness.namespace, surface="experimental-state"
    )
    assert (
        harness.simulate_gated_effect("P1", gate_token=None, writer_id="scheduler")
        is Decision.DENY
    )
    assert harness.mutation_count == 0


def test_external_synthetic_gate_still_cannot_cross_boundary() -> None:
    harness = bound_harness()
    harness.propose("P1", target_namespace="reis://canonical", surface="canonical")
    assert (
        harness.simulate_gated_effect(
            "P1",
            gate_token=harness.external_gate_token,
            writer_id="scheduler",
        )
        is Decision.DENY
    )
    assert harness.mutation_count == 0


def test_single_writer_enforced() -> None:
    harness = bound_harness()
    assert harness.bind_writer("scheduler-2") is Decision.DENY
    assert harness.writer_id == "scheduler"


def test_single_stop_and_post_stop_fencing() -> None:
    harness = bound_harness()
    assert harness.stop(StopReason.BOUND_COMPLETE) is Decision.ALLOW
    before = harness.mutation_count
    assert harness.stop(StopReason.FAIL) is Decision.DENY
    assert (
        harness.request_mutation(
            target_namespace=harness.namespace,
            surface="experimental-state",
            writer_id="scheduler",
        )
        is Decision.DENY
    )
    assert harness.mutation_count == before
    assert harness.stop_reason is StopReason.BOUND_COMPLETE


@pytest.mark.parametrize("reason", [StopReason.NO_PROGRESS, StopReason.FAIL])
def test_terminal_reasons_fence_generation(reason: StopReason) -> None:
    harness = bound_harness()
    assert harness.stop(reason) is Decision.ALLOW
    assert harness.stopped is True
    assert harness.bind_writer("scheduler") is Decision.DENY


def test_recovery_is_deterministic_and_stopped_generation_stays_stopped() -> None:
    harness = bound_harness()
    harness.stop(StopReason.NO_PROGRESS)
    checkpoint = harness.checkpoint()
    recovered = SyntheticPretrialHarness.recover(
        checkpoint,
        expected_l0_hash=harness.l0_hash,
        expected_authority_envelope_hash=harness.authority_envelope_hash,
        expected_namespace=harness.namespace,
        allowed_tools=harness.allowed_tools,
    )
    assert recovered.stopped is True
    assert recovered.stop_reason is StopReason.NO_PROGRESS
    assert recovered.writer_id == "scheduler"
    assert recovered.mutation_count == harness.mutation_count


def test_recovery_cannot_change_l0_identity() -> None:
    harness = bound_harness()
    checkpoint = harness.checkpoint()
    with pytest.raises(ValueError, match=StopReason.VOID_IDENTITY.value):
        SyntheticPretrialHarness.recover(
            checkpoint,
            expected_l0_hash="DIFFERENT_L0",
            expected_authority_envelope_hash=harness.authority_envelope_hash,
            expected_namespace=harness.namespace,
            allowed_tools=harness.allowed_tools,
        )


def test_recovery_cannot_expand_tool_authority() -> None:
    harness = bound_harness()
    checkpoint = harness.checkpoint()
    expanded = harness.allowed_tools | {"network"}
    with pytest.raises(ValueError, match=StopReason.VOID_PROTOCOL.value):
        SyntheticPretrialHarness.recover(
            checkpoint,
            expected_l0_hash=harness.l0_hash,
            expected_authority_envelope_hash=harness.authority_envelope_hash,
            expected_namespace=harness.namespace,
            allowed_tools=expanded,
        )


def test_evidence_chain_is_sealed_and_tamper_detectable() -> None:
    harness = bound_harness()
    harness.request_mutation(
        target_namespace="reis://canonical",
        surface="canonical",
        writer_id="scheduler",
    )
    assert harness.verify_evidence_chain() is True
    harness.events[0] = replace(harness.events[0], event_hash="0" * 64)
    assert harness.verify_evidence_chain() is False


def test_missing_metric_evidence_is_unknown_not_zero() -> None:
    harness = SyntheticPretrialHarness()
    assert harness.metric_value({}, "M03") == "UNKNOWN"
    assert harness.metric_value({"M03": 0}, "M03") == 0


def test_valid_void_and_aborted_records_are_retained() -> None:
    harness = bound_harness()
    harness.stop(StopReason.BOUND_COMPLETE)
    valid = harness.seal_record(GenerationStatus.STOPPED)
    void = replace(valid, status=GenerationStatus.VOID, stop_reason=StopReason.VOID_PROTOCOL)
    aborted = replace(
        valid,
        status=GenerationStatus.ABORTED,
        stop_reason=StopReason.ABORT_SAFETY,
    )
    harness.records.extend([void, aborted])
    assert {record.status for record in harness.records} == {
        GenerationStatus.STOPPED,
        GenerationStatus.VOID,
        GenerationStatus.ABORTED,
    }


def test_checkpoint_content_hash_is_reproducible() -> None:
    harness = bound_harness()
    checkpoint = harness.checkpoint()
    assert harness.checkpoint_hash(checkpoint) == harness.checkpoint_hash(checkpoint)
