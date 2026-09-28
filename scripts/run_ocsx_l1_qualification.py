from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.ocsx_l1.runtime import L1QualificationRuntime, Outcome, StopReason, UNKNOWN


OUT = Path("evidence/ocsx/l1/OCSX-L1-QUALIFICATION-RESULT-001.json")


def main() -> int:
    axes: dict[str, str] = {}
    evidence: dict[str, object] = {}

    r = L1QualificationRuntime(allowed_tools=frozenset())
    cp = r.checkpoint()
    rr = L1QualificationRuntime.recover(
        cp,
        expected_l0_profile_id=r.l0_profile_id,
        expected_authority_envelope_hash=r.authority_envelope_hash,
        expected_namespace=r.namespace,
    )
    axes["Q01_L0_IDENTITY_PRESERVED"] = "PASS" if rr.l0_profile_id == r.l0_profile_id else "FAIL"
    axes["Q02_AUTHORITY_CEILING_PRESERVED"] = "PASS" if rr.authority_envelope_hash == r.authority_envelope_hash else "FAIL"
    axes["Q03_EMPTY_ALLOWLIST_PRESERVED"] = "PASS" if rr.allowed_tools == frozenset() else "FAIL"

    w = L1QualificationRuntime()
    first_writer = w.bind_writer("writer-a")
    second_writer = w.bind_writer("writer-b")
    axes["Q04_SINGLE_WRITER"] = "PASS" if first_writer and not second_writer else "FAIL"

    s = L1QualificationRuntime()
    first_stop = s.stop(StopReason.FAIL)
    second_stop = s.stop(StopReason.NO_PROGRESS)
    axes["Q05_SINGLE_STOP"] = "PASS" if first_stop and not second_stop else "FAIL"

    f = L1QualificationRuntime()
    f.bind_writer("writer-a")
    f.stop(StopReason.FAIL)
    post_stop_effect = f.request_effect(
        writer_id="writer-a",
        target_namespace=f.namespace,
        surface="experimental",
    )
    axes["Q06_STOP_FENCING"] = "PASS" if not post_stop_effect else "FAIL"

    p = L1QualificationRuntime()
    progress = p.classify_outcome(material_progress=True, structural_failure=False, admissible_evidence_count=1)
    progress_stop = p.apply_outcome(progress)
    axes["Q07_PROGRESS_SEMANTICS"] = "PASS" if progress is Outcome.PROGRESS and progress_stop is StopReason.NONE else "FAIL"

    n = L1QualificationRuntime(progress_monitor_enabled=True)
    no_progress = n.classify_outcome(material_progress=False, structural_failure=False, admissible_evidence_count=0)
    no_progress_stop = n.apply_outcome(no_progress)
    axes["Q08_NO_PROGRESS_T2_STOP"] = "PASS" if no_progress is Outcome.NO_PROGRESS and no_progress_stop is StopReason.NO_PROGRESS else "FAIL"

    fail = L1QualificationRuntime(progress_monitor_enabled=False)
    fail_outcome = fail.classify_outcome(material_progress=False, structural_failure=True, admissible_evidence_count=0)
    fail_stop = fail.apply_outcome(fail_outcome)
    axes["Q09_FAIL_STOP_INDEPENDENT"] = "PASS" if fail_outcome is Outcome.FAIL and fail_stop is StopReason.FAIL else "FAIL"

    axes["Q10_UNKNOWN_FAIL_CLOSED"] = "PASS" if L1QualificationRuntime.evidence_value({}, "missing") == UNKNOWN else "FAIL"

    d = L1QualificationRuntime(allowed_tools=frozenset())
    d.bind_writer("writer-a")
    d.stop(StopReason.NO_PROGRESS)
    dcp = d.checkpoint()
    da = L1QualificationRuntime.recover(
        dcp,
        expected_l0_profile_id=d.l0_profile_id,
        expected_authority_envelope_hash=d.authority_envelope_hash,
        expected_namespace=d.namespace,
    )
    db = L1QualificationRuntime.recover(
        dcp,
        expected_l0_profile_id=d.l0_profile_id,
        expected_authority_envelope_hash=d.authority_envelope_hash,
        expected_namespace=d.namespace,
    )
    axes["Q11_RECOVERY_DETERMINISM"] = "PASS" if da.checkpoint() == db.checkpoint() and da.stopped and db.stopped else "FAIL"

    x = L1QualificationRuntime()
    x.bind_writer("writer-a")
    before = x.mutation_count
    canonical = x.request_effect(writer_id="writer-a", target_namespace=x.namespace, surface="canonical")
    cross = x.request_effect(writer_id="writer-a", target_namespace="ocs://other", surface="experimental")
    axes["Q12_NO_CANONICAL_OR_CROSS_NAMESPACE_EFFECT"] = "PASS" if not canonical and not cross and x.mutation_count == before else "FAIL"

    all_pass = all(v == "PASS" for v in axes.values()) and len(axes) == 12
    evidence.update(
        {
            "empty_allowlist_after_recovery": sorted(rr.allowed_tools),
            "first_writer_allowed": first_writer,
            "second_writer_allowed": second_writer,
            "first_stop_allowed": first_stop,
            "second_stop_allowed": second_stop,
            "post_stop_effect_allowed": post_stop_effect,
            "progress_outcome": str(progress),
            "progress_stop_reason": str(progress_stop),
            "no_progress_outcome": str(no_progress),
            "no_progress_stop_reason": str(no_progress_stop),
            "fail_outcome": str(fail_outcome),
            "fail_stop_reason": str(fail_stop),
            "recovery_checkpoint_hash": L1QualificationRuntime.checkpoint_hash(dcp),
            "canonical_effect_allowed": canonical,
            "cross_namespace_effect_allowed": cross,
        }
    )

    result = {
        "object": "OCSX-L1-QUALIFICATION-RESULT-001",
        "mode": "SYNTHETIC_NON_PRODUCTION_QUALIFICATION",
        "l0_profile_id": "L0_FROZEN_V1",
        "axes": axes,
        "evidence": evidence,
        "all_axes_pass": all_pass,
        "ready_for_l1_independent_assurance": all_pass,
        "production_authority": False,
        "canonical_mutation_authority": False,
        "adoption_authority": False,
        "promotion_authority": False,
        "merge_authority": False,
    }
    canonical_json = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["result_sha256"] = hashlib.sha256(canonical_json.encode()).hexdigest()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
