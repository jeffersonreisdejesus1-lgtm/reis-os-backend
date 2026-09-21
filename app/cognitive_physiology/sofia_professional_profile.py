from __future__ import annotations

from dataclasses import dataclass

ROADMAP_SOURCE = "https://roadmap.sh/"
ROADMAP_SOURCE_TYPE = "community_created_professional_roadmap"


@dataclass(frozen=True)
class ProfessionalCompetency:
    competency_id: str
    name: str
    roadmap_tracks: tuple[str, ...]
    capability: str
    skill_id: str
    evidence_requirements: tuple[str, ...]
    authority_effect: str = "NONE"


SOFIA_PROFESSIONAL_COMPETENCIES: tuple[ProfessionalCompetency, ...] = (
    ProfessionalCompetency(
        "SOFIA-CS",
        "computer_science_foundations",
        ("computer-science",),
        "reason_about_software_foundations",
        "software-foundations",
        ("design_note", "validated_test"),
    ),
    ProfessionalCompetency(
        "SOFIA-PYTHON",
        "python_implementation",
        ("python",),
        "implement_python_software",
        "python-implementation",
        ("changed_files", "tests", "receipt"),
    ),
    ProfessionalCompetency(
        "SOFIA-GIT",
        "version_control_and_github",
        ("git-and-github",),
        "manage_versioned_change",
        "git-change-management",
        ("commit", "readback"),
    ),
    ProfessionalCompetency(
        "SOFIA-QA",
        "testing_and_quality_assurance",
        ("qa", "code-review"),
        "qualify_software_change",
        "software-test-qualification",
        ("pytest", "ruff", "mypy", "test_evidence"),
    ),
    ProfessionalCompetency(
        "SOFIA-BACKEND",
        "backend_and_api_engineering",
        ("backend",),
        "implement_backend_contract",
        "backend-contract-implementation",
        ("contract_test", "api_evidence"),
    ),
    ProfessionalCompetency(
        "SOFIA-ARCH",
        "software_architecture",
        ("software-architect", "design-and-architecture"),
        "implement_within_architectural_boundary",
        "architecture-boundary-compliance",
        ("architecture_reference", "review_receipt"),
    ),
    ProfessionalCompetency(
        "SOFIA-SYSTEM-DESIGN",
        "system_design",
        ("system-design",),
        "reason_about_runtime_boundaries",
        "system-design-analysis",
        ("decision_record", "failure_analysis"),
    ),
    ProfessionalCompetency(
        "SOFIA-CICD",
        "continuous_delivery",
        ("devops",),
        "prepare_reproducible_delivery",
        "ci-delivery-preparation",
        ("pipeline_log", "artifact", "readback"),
    ),
)


def validate_sofia_professional_profile() -> None:
    if len(SOFIA_PROFESSIONAL_COMPETENCIES) != 8:
        raise ValueError("eight_sofia_competencies_required")
    identifiers = {item.competency_id for item in SOFIA_PROFESSIONAL_COMPETENCIES}
    if len(identifiers) != len(SOFIA_PROFESSIONAL_COMPETENCIES):
        raise ValueError("competency_identity_collision")
    if any(item.authority_effect != "NONE" for item in SOFIA_PROFESSIONAL_COMPETENCIES):
        raise ValueError("professional_competency_cannot_grant_authority")
    if any(not item.evidence_requirements for item in SOFIA_PROFESSIONAL_COMPETENCIES):
        raise ValueError("competency_evidence_required")
