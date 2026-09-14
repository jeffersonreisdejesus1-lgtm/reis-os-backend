from __future__ import annotations

from dataclasses import replace

from app.c09_acceptance import (
    FROZEN_PI_IDS,
    PI_ACCEPTANCE_MANIFEST,
    AcceptanceObservation,
    evaluate_acceptance,
)


def _observation(pi_id: str, **overrides: object) -> AcceptanceObservation:
    values: dict[str, object] = {
        "pi_id": pi_id,
        "trace_id": f"trace:{pi_id}",
        "correlation_id": f"corr:{pi_id}",
        "scenario_id": f"C09-E2E-{pi_id}",
        "reachable": True,
        "consumed": True,
        "causal_contribution_observed": True,
        "traceable": True,
        "governed": True,
        "persistence_verified": None,
        "recovery_verified": None,
        "observable_consequence_ref": f"observable:{pi_id}",
    }
    values.update(overrides)
    return AcceptanceObservation(**values)  # type: ignore[arg-type]


def test_c09_manifest_has_exactly_frozen_36_unique_pi_identities() -> None:
    assert len(FROZEN_PI_IDS) == 36
    assert len(set(FROZEN_PI_IDS)) == 36
    assert len(PI_ACCEPTANCE_MANIFEST) == 36
    assert tuple(entry.pi_id for entry in PI_ACCEPTANCE_MANIFEST) == FROZEN_PI_IDS


def test_c09_every_manifest_entry_binds_required_acceptance_fields() -> None:
    for entry in PI_ACCEPTANCE_MANIFEST:
        assert entry.profile_or_universal_owner
        assert entry.producer
        assert entry.input_ref
        assert entry.trigger
        assert entry.consumer
        assert entry.reachability_probe
        assert entry.causal_contribution_assertion
        assert entry.authority_boundary
        assert entry.end_to_end_scenario_id
        assert entry.expected_observable_consequence
        assert entry.negative_or_mutation_probe
        assert entry.acceptance_status == "NOT_PROVEN"


def test_c09_missing_native_run_can_never_be_promoted_by_manifest_presence() -> None:
    evaluated, summary = evaluate_acceptance(PI_ACCEPTANCE_MANIFEST, ())
    assert all(entry.acceptance_status == "NOT_PROVEN" for entry in evaluated)
    assert summary.manifest_cardinality == 36
    assert summary.unique_pi_ids == 36
    assert summary.accepted_pi_count == 0
    assert summary.unresolved_pi_count == 36
    assert summary.c09_pass is False


def test_c09_reachability_without_consumption_or_causality_is_not_accepted() -> None:
    pi_id = FROZEN_PI_IDS[0]
    observation = _observation(
        pi_id,
        consumed=False,
        causal_contribution_observed=False,
    )
    evaluated, summary = evaluate_acceptance(
        PI_ACCEPTANCE_MANIFEST,
        (observation,),
    )
    first = next(entry for entry in evaluated if entry.pi_id == pi_id)
    assert first.acceptance_status == "NOT_PROVEN"
    assert summary.accepted_pi_count == 0
    assert summary.c09_pass is False


def test_c09_one_complete_observation_accepts_only_that_pi_not_global_plenitude(
) -> None:
    pi_id = FROZEN_PI_IDS[0]
    evaluated, summary = evaluate_acceptance(
        PI_ACCEPTANCE_MANIFEST,
        (_observation(pi_id),),
    )
    accepted = [entry for entry in evaluated if entry.acceptance_status == "ACCEPTED"]
    assert [entry.pi_id for entry in accepted] == [pi_id]
    assert summary.accepted_pi_count == 1
    assert summary.unresolved_pi_count == 35
    assert summary.c09_pass is False


def test_c09_required_persistence_and_recovery_fail_closed() -> None:
    target = replace(
        PI_ACCEPTANCE_MANIFEST[0],
        persistence_requirement="REQUIRED",
        recovery_requirement="REQUIRED",
    )
    manifest = (target, *PI_ACCEPTANCE_MANIFEST[1:])
    observation = _observation(
        target.pi_id,
        persistence_verified=False,
        recovery_verified=False,
    )
    evaluated, summary = evaluate_acceptance(manifest, (observation,))
    assert evaluated[0].acceptance_status == "NOT_PROVEN"
    assert summary.untested_required_persistence == 1
    assert summary.untested_required_recovery == 1
    assert summary.c09_pass is False


def test_c09_global_pass_requires_36_complete_native_observations() -> None:
    observations = tuple(_observation(pi_id) for pi_id in FROZEN_PI_IDS)
    evaluated, summary = evaluate_acceptance(
        PI_ACCEPTANCE_MANIFEST,
        observations,
    )
    assert all(entry.acceptance_status == "ACCEPTED" for entry in evaluated)
    assert summary.accepted_pi_count == 36
    assert summary.unresolved_pi_count == 0
    assert summary.global_end_to_end_paths_native_and_reproducible is True
    assert summary.c09_pass is True
