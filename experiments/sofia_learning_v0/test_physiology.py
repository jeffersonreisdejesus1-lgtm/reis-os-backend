from experiments.sofia_learning_v0.physiology import (
    EvidenceRef,
    LearningState,
    LearningStatus,
    RetrievalPolicy,
)


def passing(ref: str = "test") -> tuple[EvidenceRef, ...]:
    return (EvidenceRef(ref=ref, verdict="PASS"),)


def test_unverified_learning_is_not_retrieved():
    state = LearningState()
    state.append_candidate(
        experience_id="e1", category="parsing", problem="parse a switch",
        solution="normalize then map", outcome="pass", evidence=passing(),
    )
    assert state.retrieve("parse switch", "parsing") == []


def test_verified_learning_is_retrievable_and_category_weighted():
    state = LearningState()
    state.append_candidate(experience_id="e1", category="parsing", problem="parse bool", solution="normalize map", outcome="pass", evidence=passing())
    state.verify("e1")
    state.append_candidate(experience_id="e2", category="collections", problem="dedupe", solution="preserve order", outcome="pass", evidence=passing())
    state.verify("e2")
    result = state.retrieve("parse switch", "parsing", k=1)
    assert result[0].experience_id == "e1"


def test_failed_evidence_cannot_promote_learning():
    state = LearningState()
    state.append_candidate(experience_id="e1", category="x", problem="p", solution="s", outcome="fail", evidence=(EvidenceRef("r", "FAIL"),))
    try:
        state.verify("e1")
    except ValueError:
        pass
    else:
        raise AssertionError("verification must fail closed")


def test_supersession_preserves_history_and_excludes_old_record():
    state = LearningState()
    state.append_candidate(experience_id="e1", category="reliability", problem="retry", solution="old", outcome="pass", evidence=passing("old"))
    state.verify("e1")
    new = state.supersede("e1", "e2", category="reliability", problem="retry", solution="new", outcome="pass", evidence=passing("new"))
    assert new.status is LearningStatus.VERIFIED
    assert [x.experience_id for x in state.retrieve("retry", "reliability")] == ["e2"]
    old = next(x for x in state.records if x.experience_id == "e1")
    assert old.status is LearningStatus.SUPERSEDED


def test_rollback_removes_learning_from_active_retrieval():
    state = LearningState()
    state.append_candidate(experience_id="e1", category="implementation", problem="feature", solution="pattern", outcome="pass", evidence=passing())
    state.verify("e1")
    marker = state.rollback("e1", "rb1", passing("rollback"))
    assert marker.rollback_of == "e1"
    assert state.retrieve("feature", "implementation") == []


def test_external_parametric_policy_is_separate_and_validated():
    state = LearningState()
    state.update_external_policy(RetrievalPolicy(2.0, 2.0, 1.0, 0.1))
    assert state.policy.category_match_weight == 2.0
    try:
        state.update_external_policy(RetrievalPolicy(-1, 1, 1, 1))
    except ValueError:
        pass
    else:
        raise AssertionError("negative policy weights must be rejected")


def test_candidate_deduplication_and_append_only_identity():
    state = LearningState()
    first = state.append_candidate(experience_id="e1", category="x", problem="p", solution="s", outcome="pass", evidence=passing())
    try:
        state.append_candidate(experience_id="e1", category="x", problem="p2", solution="s2", outcome="pass", evidence=passing())
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate IDs must fail")
    assert state.records[0].content_hash == first.content_hash
