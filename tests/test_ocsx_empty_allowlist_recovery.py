from app.ocsx_pretrial import StopReason, SyntheticPretrialHarness


def test_recovery_preserves_explicit_empty_tool_allowlist() -> None:
    harness = SyntheticPretrialHarness(
        generation_id="OCSX-TRIAL-EMPTY-ALLOWLIST",
        namespace="ocsx://experiment/trial/empty-allowlist",
        l0_hash="L0_FROZEN_V1",
        allowed_tools=frozenset(),
    )
    harness.bind_writer("scheduler")
    harness.stop(StopReason.BOUND_COMPLETE)
    checkpoint = harness.checkpoint()
    expected_authority = harness.authority_envelope_hash

    recovered = SyntheticPretrialHarness.recover(
        checkpoint,
        expected_l0_hash=harness.l0_hash,
        expected_authority_envelope_hash=expected_authority,
        expected_namespace=harness.namespace,
        allowed_tools=frozenset(),
    )

    assert recovered.allowed_tools == frozenset()
    assert recovered.authority_envelope_hash == expected_authority
    assert recovered.stopped is True
    assert recovered.stop_reason is StopReason.BOUND_COMPLETE
