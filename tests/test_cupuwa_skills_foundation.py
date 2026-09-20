import pytest

from app.cupuwa_skills import SkillDescriptor, SkillRegistry, resolve_skill


def registry() -> SkillRegistry:
    return SkillRegistry(
        [
            SkillDescriptor(
                skill_id="SOFTWARE-TEST-QUALIFICATION",
                version="1.0.0",
                capabilities=frozenset({"run_tests"}),
                compatible_ocs=frozenset({"SOFIA"}),
            )
        ]
    )


def test_resolves_one_validated_skill_with_authority_reference() -> None:
    result = resolve_skill(
        registry(),
        capability="run_tests",
        ocs_id="SOFIA",
        authority_ref="authority:mission-1",
    )
    assert result.skill.skill_id == "SOFTWARE-TEST-QUALIFICATION"


def test_missing_authority_fails_closed() -> None:
    with pytest.raises(PermissionError, match="authority_reference"):
        resolve_skill(registry(), capability="run_tests", ocs_id="SOFIA", authority_ref=None)


def test_unknown_capability_fails_closed() -> None:
    with pytest.raises(LookupError, match="not_unique"):
        resolve_skill(registry(), capability="deploy", ocs_id="SOFIA", authority_ref="authority:mission-1")


def test_skill_cannot_grant_authority() -> None:
    with pytest.raises(ValueError, match="grant_authority"):
        SkillDescriptor(
            skill_id="BAD",
            version="1.0.0",
            capabilities=frozenset({"run_tests"}),
            compatible_ocs=frozenset({"SOFIA"}),
            authority_granted="WRITE_REPO",
        )
