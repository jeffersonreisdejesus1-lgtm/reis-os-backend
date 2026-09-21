from __future__ import annotations

from app.cognitive_physiology.sofia_professional_profile import (
    ROADMAP_SOURCE,
    SOFIA_PROFESSIONAL_COMPETENCIES,
    validate_sofia_professional_profile,
)


def test_sofia_profile_uses_roadmap_source() -> None:
    assert ROADMAP_SOURCE == "https://roadmap.sh/"


def test_sofia_profile_has_eight_competencies() -> None:
    validate_sofia_professional_profile()
    assert len(SOFIA_PROFESSIONAL_COMPETENCIES) == 8


def test_every_competency_maps_to_capability_and_skill() -> None:
    assert all(
        item.capability and item.skill_id
        for item in SOFIA_PROFESSIONAL_COMPETENCIES
    )


def test_competencies_do_not_grant_authority() -> None:
    assert all(
        item.authority_effect == "NONE"
        for item in SOFIA_PROFESSIONAL_COMPETENCIES
    )


def test_every_competency_requires_evidence() -> None:
    assert all(item.evidence_requirements for item in SOFIA_PROFESSIONAL_COMPETENCIES)
