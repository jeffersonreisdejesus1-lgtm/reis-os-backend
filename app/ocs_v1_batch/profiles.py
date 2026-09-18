from __future__ import annotations

from app.ocs_v1_batch.contracts import CandidateProfile, GovernorSpec


def _g(ocs: str, n: int, role: str, namespace: str, keys: tuple[str, ...], operation: str) -> GovernorSpec:
    return GovernorSpec(
        governor_id=f"GOV-{ocs}-{n:02d}",
        role=role,
        writable_namespaces=(namespace,),
        owned_state_keys=keys,
        allowed_operations=(operation,),
    )


PROFILES: dict[str, CandidateProfile] = {
    "DEDALA": CandidateProfile(
        ocs_id="DEDALA",
        identity_ref="REIS OS — Evolution Core — Dédala / 3c9d31bc-7b67-81d1-a02f-fe2a6e21ecfa",
        derivation_ref="DEDALA-V1-LOCAL-GOVERNOR-DERIVATION-001",
        specialization="architecture + engineering + security + systems + integration",
        governors=(
            _g("DEDALA", 1, "ARCHITECTURAL_CONSTRAINT_GOVERNOR", "REVIEW_WORKING_STATE", ("constraints", "architecture_integrity"), "SET_CONSTRAINT_STATE"),
            _g("DEDALA", 2, "THREAT_RISK_GOVERNOR", "REVIEW_WORKING_STATE", ("threats", "risk"), "SET_RISK_STATE"),
            _g("DEDALA", 3, "CAUSAL_INTEGRATION_GOVERNOR", "REVIEW_WORKING_STATE", ("causal_chain", "integration"), "SET_CAUSAL_STATE"),
            _g("DEDALA", 4, "FINDING_ROUTING_GOVERNOR", "FINDING_STATE", ("finding", "route"), "SET_FINDING_STATE"),
        ),
        binding_refs={
            "R1_R7_BINDING_REF": "DEDALA-V1-R1-R7-STATE-CONTRACT-001",
            "R2_R7_BINDING_REF": "DEDALA-V1-R2-R7-MEASUREMENT-CONTRACT-001",
            "R3_R7_BINDING_REF": "DEDALA-V1-R3-R7-TRANSITION-CONTRACT-001",
            "R4_R7_BINDING_REF": "DEDALA-V1-R4-R7-SCHEDULING-CONTRACT-001",
            "R5_R7_BINDING_REF": "DEDALA-V1-R5-R7-EVIDENCE-CONTRACT-001",
            "R6_R7_BINDING_REF": "DEDALA-V1-R6-R7-CONSTRAINT-CONTRACT-001",
        },
        namespaces=("INSTITUTIONAL_STATE", "REVIEW_WORKING_STATE", "FINDING_STATE", "EVIDENCE_STATE", "RECOVERY_STATE"),
        deterministic_policies=("NO_SELF_ASSURANCE", "EXACT_EVIDENCE_PROVENANCE", "DENY_ZERO_MUTATION", "CAUSAL_INCONSISTENCY_HOLD"),
        preserved_reservations=("HISTORICAL_RUNTIME_OBSERVABILITY_RESERVATIONS",),
    ),
    "AGORA": CandidateProfile(
        ocs_id="AGORA",
        identity_ref="REIS OS — Evolution Core — Ágora / 3c9d31bc-7b67-81fa-8e5c-f952171f5c2b",
        derivation_ref="AGORA-V1-LOCAL-GOVERNOR-DERIVATION-001",
        specialization="independent software audit + technical QA",
        governors=(
            _g("AGORA", 1, "SOFTWARE_VERIFICATION_INTAKE_GOVERNOR", "VERIFICATION_WORKING_STATE", ("intake", "object_ref"), "SET_VERIFICATION_INTAKE"),
            _g("AGORA", 2, "TECHNICAL_QA_CRITERIA_GOVERNOR", "VERIFICATION_WORKING_STATE", ("qa_criteria", "test_matrix"), "SET_QA_CRITERIA"),
            _g("AGORA", 3, "EVIDENCE_SUFFICIENCY_RISK_GOVERNOR", "EVIDENCE_STATE", ("evidence_sufficiency", "implementation_risk"), "SET_EVIDENCE_RISK"),
            _g("AGORA", 4, "DEFECT_CONFORMANCE_ROUTING_GOVERNOR", "FINDING_STATE", ("defect_class", "conformance_route"), "SET_CONFORMANCE_FINDING"),
        ),
        binding_refs={
            "R1_R7_BINDING_REF": "AGORA-V1-R1-R7-VERIFICATION-STATE-CONTRACT-001",
            "R2_R7_BINDING_REF": "AGORA-V1-R2-R7-MEASUREMENT-CONTRACT-001",
            "R3_R7_BINDING_REF": "AGORA-V1-R3-R7-FINDING-TRANSITION-CONTRACT-001",
            "R4_R7_BINDING_REF": "AGORA-V1-R4-R7-SCHEDULING-CONTRACT-001",
            "R5_R7_BINDING_REF": "AGORA-V1-R5-R7-EVIDENCE-LINEAGE-CONTRACT-001",
            "R6_R7_BINDING_REF": "AGORA-V1-R6-R7-SCOPE-AUTHORITY-CONTRACT-001",
        },
        namespaces=("AUDIT_STATE", "VERIFICATION_WORKING_STATE", "FINDING_STATE", "EVIDENCE_STATE", "RECOVERY_STATE"),
        deterministic_policies=("EXACT_IMPLEMENTATION_OBJECT_HEAD_BINDING", "MISSING_EVIDENCE_NOT_PASS", "NO_SELF_ASSURANCE", "NO_TARGET_NAMESPACE_MUTATION"),
        preserved_reservations=("HISTORICAL_RUNTIME_OBSERVABILITY_RESERVATIONS",),
    ),
    "SOFIA": CandidateProfile(
        ocs_id="SOFIA",
        identity_ref="REIS OS — Evolution Core — Sofia / 3c9d31bc-7b67-81c3-bb79-e17ebe2017e6",
        derivation_ref="SOFIA-V1-LOCAL-GOVERNOR-DERIVATION-001",
        specialization="engineering + implementation",
        governors=(
            _g("SOFIA", 1, "IMPLEMENTATION_PLANNING_GOVERNOR", "CHANGE_PLAN_STATE", ("plan", "scope"), "SET_IMPLEMENTATION_PLAN"),
            _g("SOFIA", 2, "REPOSITORY_CHANGE_GOVERNOR", "IMPLEMENTATION_STATE", ("repository_object", "change_set"), "SET_REPOSITORY_CHANGE"),
            _g("SOFIA", 3, "DEPENDENCY_INTEGRATION_GOVERNOR", "IMPLEMENTATION_STATE", ("dependencies", "integration"), "SET_DEPENDENCY_INTEGRATION"),
            _g("SOFIA", 4, "TEST_ROLLBACK_REPAIR_GOVERNOR", "TEST_STATE", ("tests", "rollback", "repair_route"), "SET_TEST_ROLLBACK"),
        ),
        binding_refs={
            "R1_R7_BINDING_REF": "SOFIA-V1-R1-R7-IMPLEMENTATION-STATE-CONTRACT-001",
            "R2_R7_BINDING_REF": "SOFIA-V1-R2-R7-PROGRESS-CONTRACT-001",
            "R3_R7_BINDING_REF": "SOFIA-V1-R3-R7-CHANGE-TRANSITION-CONTRACT-001",
            "R4_R7_BINDING_REF": "SOFIA-V1-R4-R7-SCHEDULING-CONTRACT-001",
            "R5_R7_BINDING_REF": "SOFIA-V1-R5-R7-IMPLEMENTATION-EVIDENCE-CONTRACT-001",
            "R6_R7_BINDING_REF": "SOFIA-V1-R6-R7-WRITE-AUTHORITY-CONTRACT-001",
        },
        namespaces=("IMPLEMENTATION_STATE", "CHANGE_PLAN_STATE", "TEST_STATE", "EVIDENCE_STATE", "RECOVERY_STATE"),
        deterministic_policies=("EXACT_REPOSITORY_OBJECT_BINDING", "NO_MERGE_AUTHORITY", "OWNER_SCOPED_WRITES", "NO_SELF_ASSURANCE"),
        preserved_reservations=("HISTORICAL_HOSTED_RUNTIME_RESERVATIONS",),
    ),
    "METIS": CandidateProfile(
        ocs_id="METIS",
        identity_ref="REIS OS — Evolution Core — Mêtis / 3c9d31bc-7b67-8189-8614-e8f9fc0e6dac",
        derivation_ref="METIS-V1-LOCAL-GOVERNOR-DERIVATION-001",
        specialization="intelligence + research + strategy + market",
        governors=(
            _g("METIS", 1, "RESEARCH_INTAKE_GOVERNOR", "RESEARCH_STATE", ("research_intake", "scope"), "SET_RESEARCH_INTAKE"),
            _g("METIS", 2, "SOURCE_EVIDENCE_QUALITY_GOVERNOR", "SOURCE_STATE", ("source_quality", "evidence_quality"), "SET_SOURCE_QUALITY"),
            _g("METIS", 3, "UNCERTAINTY_CLAIM_CALIBRATION_GOVERNOR", "CLAIM_STATE", ("claim", "uncertainty", "confidence"), "SET_CLAIM_CALIBRATION"),
            _g("METIS", 4, "STRATEGIC_SYNTHESIS_ROUTING_GOVERNOR", "STRATEGY_STATE", ("synthesis", "opportunity_risk_route"), "SET_STRATEGY_SYNTHESIS"),
        ),
        binding_refs={
            "R1_R7_BINDING_REF": "METIS-V1-R1-R7-CLAIM-STATE-CONTRACT-001",
            "R2_R7_BINDING_REF": "METIS-V1-R2-R7-CONFIDENCE-CONTRACT-001",
            "R3_R7_BINDING_REF": "METIS-V1-R3-R7-EVIDENCE-CLAIM-TRANSITION-CONTRACT-001",
            "R4_R7_BINDING_REF": "METIS-V1-R4-R7-RESEARCH-SCHEDULING-CONTRACT-001",
            "R5_R7_BINDING_REF": "METIS-V1-R5-R7-PROVENANCE-FRESHNESS-CONTRACT-001",
            "R6_R7_BINDING_REF": "METIS-V1-R6-R7-EVIDENCE-AUTHORITY-CONTRACT-001",
        },
        namespaces=("RESEARCH_STATE", "CLAIM_STATE", "SOURCE_STATE", "FRESHNESS_STATE", "STRATEGY_STATE", "RECOVERY_STATE"),
        deterministic_policies=("FRESHNESS_STATE_MACHINE", "SOURCE_PROVENANCE_REQUIRED", "NO_CERTAINTY_INFLATION", "STRATEGY_NOT_EXECUTION_AUTHORITY"),
        preserved_reservations=("HISTORICAL_RUNTIME_OBSERVABILITY_RESERVATIONS",),
    ),
    "AURI": CandidateProfile(
        ocs_id="AURI",
        identity_ref="REIS OS — Evolution Core — Auri / 3c9d31bc-7b67-812f-be12-f20a86077669",
        derivation_ref="AURI-V1-LOCAL-GOVERNOR-DERIVATION-001",
        specialization="administration + coordination + system of record",
        governors=(
            _g("AURI", 1, "ADMINISTRATIVE_INTAKE_GOVERNOR", "ADMIN_STATE", ("admin_intake", "scope"), "SET_ADMIN_INTAKE"),
            _g("AURI", 2, "RECORD_INTEGRITY_GOVERNOR", "REGISTRY_STATE", ("record", "integrity"), "SET_RECORD_INTEGRITY"),
            _g("AURI", 3, "COORDINATION_RECEIPT_GOVERNOR", "COORDINATION_STATE", ("coordination", "receipt_ref"), "SET_COORDINATION_RECEIPT"),
            _g("AURI", 4, "IDENTITY_CONTINUITY_ROUTING_GOVERNOR", "RECOVERY_STATE", ("identity_continuity", "recovery_route"), "SET_IDENTITY_CONTINUITY"),
        ),
        binding_refs={
            "R1_R7_BINDING_REF": "AURI-V1-R1-R7-ADMIN-STATE-CONTRACT-001",
            "R2_R7_BINDING_REF": "AURI-V1-R2-R7-COMPLETENESS-CONTRACT-001",
            "R3_R7_BINDING_REF": "AURI-V1-R3-R7-RECORD-HANDOFF-CONTRACT-001",
            "R4_R7_BINDING_REF": "AURI-V1-R4-R7-COORDINATION-SCHEDULING-CONTRACT-001",
            "R5_R7_BINDING_REF": "AURI-V1-R5-R7-PROVENANCE-RECEIPT-CONTRACT-001",
            "R6_R7_BINDING_REF": "AURI-V1-R6-R7-IDENTITY-AUTHORITY-CONTRACT-001",
        },
        namespaces=("ADMIN_STATE", "REGISTRY_STATE", "COORDINATION_STATE", "PROVENANCE_STATE", "RECEIPT_STATE", "RECOVERY_STATE"),
        deterministic_policies=("SYSTEM_OF_RECORD_NOT_AUTHORITY", "HISTORICAL_V04_NOT_CURRENT_PROOF", "NO_CROSS_OCS_IDENTITY_MEMORY_MERGE", "EXACT_IDENTITY_BOUND_WRITES"),
        preserved_reservations=("AURI_V04_PROVENANCE_RESERVATION_OPEN", "HISTORICAL_RUNTIME_OBSERVABILITY_RESERVATIONS"),
    ),
    "SYNERGEIA": CandidateProfile(
        ocs_id="SYNERGEIA",
        identity_ref="REIS OS — Evolution Core — Synergeia / 3c9d31bc-7b67-81c4-adc3-efa9da150537",
        derivation_ref="SYNERGEIA-V1-LOCAL-GOVERNOR-DERIVATION-001",
        specialization="GTM + activation + market coordination",
        governors=(
            _g("SYNERGEIA", 1, "ACTIVATION_INTAKE_GOVERNOR", "ACTIVATION_STATE", ("activation_intake", "prerequisites"), "SET_ACTIVATION_INTAKE"),
            _g("SYNERGEIA", 2, "CHANNEL_MARKET_COORDINATION_GOVERNOR", "CHANNEL_STATE", ("channel", "market_coordination"), "SET_CHANNEL_COORDINATION"),
            _g("SYNERGEIA", 3, "PREREQUISITE_AUTHORITY_VALIDATION_GOVERNOR", "ACTIVATION_STATE", ("authority_validation", "scope_risk"), "SET_AUTHORITY_VALIDATION"),
            _g("SYNERGEIA", 4, "DELIVERY_RETURN_ROUTING_GOVERNOR", "DELIVERY_STATE", ("package_id", "return_route"), "SET_DELIVERY_RETURN"),
        ),
        binding_refs={
            "R1_R7_BINDING_REF": "SYNERGEIA-V1-R1-R7-ACTIVATION-STATE-CONTRACT-001",
            "R2_R7_BINDING_REF": "SYNERGEIA-V1-R2-R7-READINESS-CONTRACT-001",
            "R3_R7_BINDING_REF": "SYNERGEIA-V1-R3-R7-ACTIVATION-HANDOFF-CONTRACT-001",
            "R4_R7_BINDING_REF": "SYNERGEIA-V1-R4-R7-GTM-SCHEDULING-CONTRACT-001",
            "R5_R7_BINDING_REF": "SYNERGEIA-V1-R5-R7-DELIVERY-EVIDENCE-CONTRACT-001",
            "R6_R7_BINDING_REF": "SYNERGEIA-V1-R6-R7-CHANNEL-AUTHORITY-CONTRACT-001",
        },
        namespaces=("ACTIVATION_STATE", "CHANNEL_STATE", "DELIVERY_STATE", "RETURN_STATE", "EVIDENCE_STATE", "RECOVERY_STATE"),
        deterministic_policies=("CHANNEL_AUTHORITY_REQUIRED", "PACKAGE_IDENTITY_STABLE", "RETURN_RECEIPT_BINDS_ORIGINAL", "HANDOFF_NOT_AUTHORITY_TRANSFER"),
        preserved_reservations=("HISTORICAL_RUNTIME_OBSERVABILITY_RESERVATIONS",),
    ),
    "LYRA": CandidateProfile(
        ocs_id="LYRA",
        identity_ref="REIS OS — Evolution Core — Lyra / 3c9d31bc-7b67-812c-9e35-f539331ad7b7",
        derivation_ref="LYRA-V1-LOCAL-GOVERNOR-DERIVATION-001",
        specialization="branding + identity + positioning + language + brand communication",
        governors=(
            _g("LYRA", 1, "BRAND_INTAKE_GOVERNOR", "BRAND_STATE", ("brand_intake", "brand_scope"), "SET_BRAND_INTAKE"),
            _g("LYRA", 2, "IDENTITY_POSITIONING_CONSISTENCY_GOVERNOR", "POSITIONING_STATE", ("brand_identity", "positioning"), "SET_IDENTITY_POSITIONING"),
            _g("LYRA", 3, "LANGUAGE_COMMUNICATION_COHERENCE_GOVERNOR", "LANGUAGE_STATE", ("language", "tone", "communication"), "SET_LANGUAGE_COMMUNICATION"),
            _g("LYRA", 4, "BRAND_OWNERSHIP_HANDOFF_GOVERNOR", "OWNERSHIP_STATE", ("brand_owner", "handoff"), "SET_BRAND_OWNERSHIP_HANDOFF"),
        ),
        binding_refs={
            "R1_R7_BINDING_REF": "LYRA-V1-R1-R7-BRAND-STATE-CONTRACT-001",
            "R2_R7_BINDING_REF": "LYRA-V1-R2-R7-CONSISTENCY-CONTRACT-001",
            "R3_R7_BINDING_REF": "LYRA-V1-R3-R7-BRAND-DECISION-CONTRACT-001",
            "R4_R7_BINDING_REF": "LYRA-V1-R4-R7-BRAND-SCHEDULING-CONTRACT-001",
            "R5_R7_BINDING_REF": "LYRA-V1-R5-R7-BRAND-EVIDENCE-CONTRACT-001",
            "R6_R7_BINDING_REF": "LYRA-V1-R6-R7-IDENTITY-OWNERSHIP-CONTRACT-001",
        },
        namespaces=("BRAND_STATE", "POSITIONING_STATE", "LANGUAGE_STATE", "EVIDENCE_STATE", "OWNERSHIP_STATE", "RECOVERY_STATE"),
        deterministic_policies=("CSP_LYRA_VNEXT_CORR_001_PRECEDENCE", "BRAND_IDENTITY_NOT_OCS_IDENTITY", "NO_IMPLICIT_OWNERSHIP_TRANSFER", "NO_CANONICAL_BRAND_PROMOTION"),
        preserved_reservations=("HISTORICAL_RUNTIME_OBSERVABILITY_RESERVATIONS",),
    ),
}

for _profile in PROFILES.values():
    _profile.validate()
