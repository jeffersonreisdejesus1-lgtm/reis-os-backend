from .physiology import LPEProfile, RetrievalPolicy

DEFAULT_POLICY = RetrievalPolicy(2.0, 2.0, 1.0, 0.1)

IRIS = LPEProfile(
    ocs="IRIS",
    specialty="UX/UI, visual design, perception, interaction, experience, accessibility",
    allowed_categories=("ux_research", "interaction", "accessibility", "visual_system", "heuristics", "handoff"),
    policy=DEFAULT_POLICY,
)

LYRA = LPEProfile(
    ocs="LYRA",
    specialty="branding, identity, positioning, language, brand communication",
    allowed_categories=("naming", "positioning", "verbal_identity", "brand_architecture", "narrative", "consistency"),
    policy=DEFAULT_POLICY,
)

DEDALA = LPEProfile(
    ocs="DEDALA",
    specialty="software/system architecture, security, integration, systems engineering, technical operations",
    allowed_categories=("architecture", "security", "integration", "runtime", "resilience", "observability", "rollback"),
    policy=DEFAULT_POLICY,
)

SYNESIS = LPEProfile(
    ocs="SYNESIS",
    specialty="independent assurance, QA, verification, testing, contradiction, institutional audit",
    allowed_categories=("assurance", "qa", "verification", "falsification", "traceability", "reproducibility", "test_adequacy"),
    policy=DEFAULT_POLICY,
)

PROFILES = {p.ocs: p for p in (IRIS, LYRA, DEDALA, SYNESIS)}
