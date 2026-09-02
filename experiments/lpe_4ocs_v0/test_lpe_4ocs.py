import pytest

from experiments.lpe_4ocs_v0.physiology import EvidenceRef, LearningState, LearningStatus, RetrievalPolicy
from experiments.lpe_4ocs_v0.profiles import IRIS, LYRA, DEDALA, SYNESIS


PROFILES = [IRIS, LYRA, DEDALA, SYNESIS]


def passing(ref: str = "test"):
    return (EvidenceRef(ref=ref, verdict="PASS"),)


@pytest.mark.parametrize("profile", PROFILES)
def test_unverified_learning_is_not_retrieved(profile):
    state = LearningState(profile)
    category = profile.allowed_categories[0]
    state.append_candidate(experience_id=f"{profile.ocs}-e1", category=category, problem="problem", solution="solution", outcome="pass", evidence=passing())
    assert state.retrieve("problem", category) == []


@pytest.mark.parametrize("profile", PROFILES)
def test_verified_learning_is_retrievable(profile):
    state = LearningState(profile)
    category = profile.allowed_categories[0]
    eid = f"{profile.ocs}-e1"
    state.append_candidate(experience_id=eid, category=category, problem="repeatable problem", solution="verified solution", outcome="pass", evidence=passing())
    state.verify(eid)
    assert state.retrieve("repeatable problem", category, k=1)[0].experience_id == eid


@pytest.mark.parametrize("profile", PROFILES)
def test_failed_evidence_blocks_promotion(profile):
    state = LearningState(profile)
    category = profile.allowed_categories[0]
    eid = f"{profile.ocs}-fail"
    state.append_candidate(experience_id=eid, category=category, problem="p", solution="s", outcome="fail", evidence=(EvidenceRef("r", "FAIL"),))
    with pytest.raises(ValueError):
        state.verify(eid)


@pytest.mark.parametrize("profile", PROFILES)
def test_supersession_and_rollback(profile):
    state = LearningState(profile)
    category = profile.allowed_categories[0]
    old = f"{profile.ocs}-old"
    new = f"{profile.ocs}-new"
    rollback_id = f"{profile.ocs}-rb"

    state.append_candidate(experience_id=old, category=category, problem="problem", solution="old", outcome="pass", evidence=passing())
    state.verify(old)
    replacement = state.supersede(old, new, category=category, problem="problem", solution="new", outcome="pass", evidence=passing())

    assert replacement.status is LearningStatus.VERIFIED
    assert state.retrieve("problem", category)[0].experience_id == new

    marker = state.rollback(new, rollback_id, passing("rollback"))

    stored = {record.experience_id: record for record in state.records}
    assert marker.rollback_of == new
    assert stored[rollback_id].rollback_of == new
    assert stored[new].status is LearningStatus.ROLLED_BACK
    assert stored[old].status is LearningStatus.VERIFIED
    assert stored[old].supersedes == new
    assert f"restore predecessor behavior:{old}" == stored[rollback_id].solution

    retrieved = state.retrieve("problem", category)
    assert retrieved
    assert retrieved[0].experience_id == old
    assert all(record.experience_id != new for record in retrieved)


@pytest.mark.parametrize("profile", PROFILES)
def test_rollback_without_superseded_predecessor_restores_baseline(profile):
    state = LearningState(profile)
    category = profile.allowed_categories[0]
    target = f"{profile.ocs}-target"
    rollback_id = f"{profile.ocs}-baseline-rb"

    state.append_candidate(experience_id=target, category=category, problem="problem", solution="solution", outcome="pass", evidence=passing())
    state.verify(target)
    state.rollback(target, rollback_id, passing("rollback"))

    stored = {record.experience_id: record for record in state.records}
    assert stored[target].status is LearningStatus.ROLLED_BACK
    assert stored[rollback_id].rollback_of == target
    assert stored[rollback_id].solution == "restore baseline behavior"
    assert state.retrieve("problem", category) == []


@pytest.mark.parametrize("profile", PROFILES)
def test_cross_specialty_category_is_blocked(profile):
    state = LearningState(profile)
    with pytest.raises(ValueError):
        state.append_candidate(experience_id=f"{profile.ocs}-x", category="foreign_category", problem="p", solution="s", outcome="pass", evidence=passing())


@pytest.mark.parametrize("profile", PROFILES)
def test_external_policy_is_validated(profile):
    state = LearningState(profile)
    state.update_external_policy(RetrievalPolicy(2.0, 2.0, 1.0, 0.1))
    with pytest.raises(ValueError):
        state.update_external_policy(RetrievalPolicy(-1.0, 1.0, 1.0, 1.0))
