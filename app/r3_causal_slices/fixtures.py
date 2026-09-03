from __future__ import annotations

from dataclasses import dataclass

from app.profile_bindings.profiles import PROFILE_VERSION

SLICE_VERSION = "r3-v0.1.0"
CAUSAL_CHAIN = (
    "GOAL",
    "COGNITIVE_PLAN",
    "ACTION_PROPOSAL",
    "EVIDENCE_ASSESSMENT",
    "AUTHORITY_LEASE_CHECK",
    "GOVERNANCE_DECISION",
    "AUTHORIZED_ACTION_ENVELOPE",
    "TOOL_BROKER",
    "THIN_EFFECTOR",
    "MATERIAL_EFFECT_ATTEMPT",
    "READBACK",
    "STATE_COMMIT_OR_NO_COMMIT",
    "CAUSAL_TRACE",
    "RECEIPT",
)


@dataclass(frozen=True)
class SliceExpectation:
    governance_result: str
    mutation_count: int
    state_delta: str
    effector_attempt: bool
    readback_oracle: str
    recovery_oracle: str | None = None


@dataclass(frozen=True)
class ReplayPackage:
    slice_id: str
    slice_definition_version: str
    input_fixture: str
    profile_id: str
    profile_version: str
    policy_snapshot: str
    authority_fixture: str
    lease_fixture: str
    evidence_fixture: str
    expectation: SliceExpectation
    trace_sequence: tuple[str, ...]
    fault_injection_hook: str | None


def _pkg(
    slice_id: str,
    profile_id: str,
    expectation: SliceExpectation,
    *,
    evidence_fixture: str = "evidence:adequate",
    lease_fixture: str = "lease:valid",
    fault: str | None = None,
) -> ReplayPackage:
    return ReplayPackage(
        slice_id=slice_id,
        slice_definition_version=SLICE_VERSION,
        input_fixture=f"fixture:{slice_id.lower()}",
        profile_id=profile_id,
        profile_version=PROFILE_VERSION,
        policy_snapshot="policy:r3-frozen",
        authority_fixture="authority:explicit",
        lease_fixture=lease_fixture,
        evidence_fixture=evidence_fixture,
        expectation=expectation,
        trace_sequence=CAUSAL_CHAIN,
        fault_injection_hook=fault,
    )


def build_replay_packages() -> dict[str, ReplayPackage]:
    not_applicable = "NOT_APPLICABLE"
    return {
        "R3-S01": _pkg(
            "R3-S01",
            "SOFIA",
            SliceExpectation("ALLOW", 1, "VERSION_ADVANCED", True, "MATCH"),
        ),
        "R3-S02": _pkg(
            "R3-S02",
            "SOFIA",
            SliceExpectation("DENY", 0, "NO_DELTA", False, not_applicable),
            fault="invalid_scope",
        ),
        "R3-S03": _pkg(
            "R3-S03",
            "MÊTIS",
            SliceExpectation("HOLD", 0, "NO_DELTA", False, not_applicable),
            evidence_fixture="evidence:insufficient-high-risk",
            fault="insufficient_evidence",
        ),
        "R3-S04": _pkg(
            "R3-S04",
            "SOFIA",
            SliceExpectation(
                "DENY_EXPIRED",
                0,
                "NO_DELTA",
                False,
                not_applicable,
            ),
            lease_fixture="lease:expired",
            fault="expire_after_issue",
        ),
        "R3-S05": _pkg(
            "R3-S05",
            "SOFIA",
            SliceExpectation(
                "DENY_REVOKED",
                0,
                "NO_DELTA",
                False,
                not_applicable,
            ),
            lease_fixture="lease:revoked",
            fault="revoke_before_execute",
        ),
        "R3-S06": _pkg(
            "R3-S06",
            "AURI",
            SliceExpectation(
                "DENY_NAMESPACE",
                0,
                "NO_CROSS_OCS_DELTA",
                False,
                not_applicable,
            ),
            fault="cross_ocs_namespace",
        ),
        "R3-S07": _pkg(
            "R3-S07",
            "SOFIA",
            SliceExpectation("DENY_ROUTE", 0, "NO_DELTA", False, not_applicable),
            fault="direct_adapter_route",
        ),
        "R3-S08": _pkg(
            "R3-S08",
            "SOFIA",
            SliceExpectation(
                "ALLOW_THEN_RECOVER",
                1,
                "RESTORED_VERIFIED_CHECKPOINT",
                True,
                "MATCH",
                "RESTORED_STATE_MATCHES_CHECKPOINT",
            ),
            fault="post_effect_failure",
        ),
        "R3-S09": _pkg(
            "R3-S09",
            "MÊTIS",
            SliceExpectation(
                "HANDOFF_NO_AUTHORITY",
                0,
                "NO_DELTA",
                False,
                not_applicable,
            ),
            fault="receiver_reuses_source_lease",
        ),
        "R3-S10": _pkg(
            "R3-S10",
            "NÓESIS",
            SliceExpectation(
                "PROFILE_DIFFERENTIATION",
                0,
                "NO_DELTA",
                False,
                not_applicable,
            ),
        ),
    }
