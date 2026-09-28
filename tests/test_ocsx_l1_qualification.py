from app.ocsx_l1.runtime import L1QualificationRuntime, Outcome, StopReason, UNKNOWN


def test_q01_l0_identity_preserved():
    r = L1QualificationRuntime()
    cp = r.checkpoint()
    rr = L1QualificationRuntime.recover(cp, expected_l0_profile_id=r.l0_profile_id, expected_authority_envelope_hash=r.authority_envelope_hash, expected_namespace=r.namespace)
    assert rr.l0_profile_id == r.l0_profile_id


def test_q02_authority_ceiling_preserved():
    r = L1QualificationRuntime(allowed_tools=frozenset())
    cp = r.checkpoint()
    rr = L1QualificationRuntime.recover(cp, expected_l0_profile_id=r.l0_profile_id, expected_authority_envelope_hash=r.authority_envelope_hash, expected_namespace=r.namespace)
    assert rr.authority_envelope_hash == r.authority_envelope_hash


def test_q03_empty_allowlist_preserved():
    r = L1QualificationRuntime(allowed_tools=frozenset())
    cp = r.checkpoint()
    rr = L1QualificationRuntime.recover(cp, expected_l0_profile_id=r.l0_profile_id, expected_authority_envelope_hash=r.authority_envelope_hash, expected_namespace=r.namespace)
    assert rr.allowed_tools == frozenset()


def test_q04_single_writer():
    r = L1QualificationRuntime()
    assert r.bind_writer('a') is True
    assert r.bind_writer('b') is False


def test_q05_single_stop():
    r = L1QualificationRuntime()
    assert r.stop(StopReason.FAIL) is True
    assert r.stop(StopReason.NO_PROGRESS) is False


def test_q06_stop_fencing():
    r = L1QualificationRuntime()
    r.bind_writer('a')
    r.stop(StopReason.FAIL)
    assert r.request_effect(writer_id='a', target_namespace=r.namespace, surface='experimental') is False


def test_q07_progress_semantics():
    r = L1QualificationRuntime()
    outcome = r.classify_outcome(material_progress=True, structural_failure=False, admissible_evidence_count=1)
    assert outcome is Outcome.PROGRESS
    assert r.apply_outcome(outcome) is StopReason.NONE


def test_q08_no_progress_t2_stop():
    r = L1QualificationRuntime(progress_monitor_enabled=True)
    outcome = r.classify_outcome(material_progress=False, structural_failure=False, admissible_evidence_count=0)
    assert outcome is Outcome.NO_PROGRESS
    assert r.apply_outcome(outcome) is StopReason.NO_PROGRESS


def test_q09_fail_stop_independent():
    r = L1QualificationRuntime(progress_monitor_enabled=False)
    outcome = r.classify_outcome(material_progress=False, structural_failure=True, admissible_evidence_count=0)
    assert outcome is Outcome.FAIL
    assert r.apply_outcome(outcome) is StopReason.FAIL


def test_q10_unknown_fail_closed():
    assert L1QualificationRuntime.evidence_value({}, 'missing') == UNKNOWN


def test_q11_recovery_determinism():
    r = L1QualificationRuntime(allowed_tools=frozenset())
    r.bind_writer('a')
    r.stop(StopReason.NO_PROGRESS)
    cp = r.checkpoint()
    a = L1QualificationRuntime.recover(cp, expected_l0_profile_id=r.l0_profile_id, expected_authority_envelope_hash=r.authority_envelope_hash, expected_namespace=r.namespace)
    b = L1QualificationRuntime.recover(cp, expected_l0_profile_id=r.l0_profile_id, expected_authority_envelope_hash=r.authority_envelope_hash, expected_namespace=r.namespace)
    assert a.checkpoint() == b.checkpoint()
    assert a.stopped and b.stopped


def test_q12_no_canonical_or_cross_namespace_effect():
    r = L1QualificationRuntime()
    r.bind_writer('a')
    before = r.mutation_count
    assert r.request_effect(writer_id='a', target_namespace=r.namespace, surface='canonical') is False
    assert r.request_effect(writer_id='a', target_namespace='ocs://other', surface='experimental') is False
    assert r.mutation_count == before
