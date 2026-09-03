from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

AcceptanceStatus = Literal["ACCEPTED", "NOT_PROVEN"]
Requirement = Literal["REQUIRED", "NOT_REQUIRED"]

FROZEN_PI_IDS: tuple[str, ...] = (
    "PI-ALLOSTASIS",
    "PI-ATTENTION",
    "PI-CAUSAL",
    "PI-CONSOLIDATION",
    "PI-DECISION",
    "PI-EMOTION-FUNCTIONAL",
    "PI-EPISODIC",
    "PI-GLOBAL-WORKSPACE",
    "PI-HOMEOSTASIS",
    "PI-IMAGINATION",
    "PI-IMMUNE",
    "PI-INHIBITION",
    "PI-INTEROCEPTION",
    "PI-LANGUAGE",
    "PI-METABOLISM",
    "PI-METACOGNITION",
    "PI-METAPLASTICITY",
    "PI-MOTIVATION",
    "PI-NOCICEPTION",
    "PI-OBSERVABILITY",
    "PI-OTHER-MODEL",
    "PI-PERCEPTION",
    "PI-PLANNING",
    "PI-PLASTICITY",
    "PI-PREDICTION",
    "PI-PREDICTION-ERROR",
    "PI-PROCEDURAL",
    "PI-PRUNING",
    "PI-REASONING",
    "PI-RECOVERY",
    "PI-REWARD",
    "PI-SALIENCE",
    "PI-SELF-MODEL",
    "PI-SEMANTIC",
    "PI-WORKING-MEMORY",
    "PI-WORLD-MODEL",
)


@dataclass(frozen=True)
class PIAcceptanceEntry:
    pi_id: str
    profile_or_universal_owner: str
    producer: str
    input_ref: str
    trigger: str
    consumer: str
    reachability_probe: str
    causal_contribution_assertion: str
    trace_id: str | None
    correlation_id: str | None
    authority_boundary: str
    state_before: str | None
    state_after: str | None
    persistence_requirement: Requirement
    recovery_requirement: Requirement
    end_to_end_scenario_id: str
    expected_observable_consequence: str
    negative_or_mutation_probe: str
    acceptance_status: AcceptanceStatus = "NOT_PROVEN"
    unresolved_reason: str | None = "native_end_to_end_run_not_bound"


@dataclass(frozen=True)
class AcceptanceObservation:
    pi_id: str
    trace_id: str
    correlation_id: str
    scenario_id: str
    reachable: bool
    consumed: bool
    causal_contribution_observed: bool
    traceable: bool
    governed: bool
    persistence_verified: bool | None = None
    recovery_verified: bool | None = None
    observable_consequence_ref: str | None = None


@dataclass(frozen=True)
class AcceptanceSummary:
    manifest_cardinality: int
    unique_pi_ids: int
    accepted_pi_count: int
    unresolved_pi_count: int
    untested_required_persistence: int
    untested_required_recovery: int
    global_end_to_end_paths_native_and_reproducible: bool

    @property
    def c09_pass(self) -> bool:
        return (
            self.manifest_cardinality == 36
            and self.unique_pi_ids == 36
            and self.accepted_pi_count == 36
            and self.unresolved_pi_count == 0
            and self.untested_required_persistence == 0
            and self.untested_required_recovery == 0
            and self.global_end_to_end_paths_native_and_reproducible
        )


def _entry(pi_id: str) -> PIAcceptanceEntry:
    return PIAcceptanceEntry(
        pi_id=pi_id,
        profile_or_universal_owner="UNIVERSAL_NATIVE_PI",
        producer="native_runtime_signal_source",
        input_ref="signal+modulation",
        trigger="PI.stimulate(signal, modulation)",
        consumer="family_population->functional_mesh->global_runtime",
        reachability_probe="native_pi_instance.stimulate",
        causal_contribution_assertion=(
            "activation_delta_must_produce_observable_downstream_consequence"
        ),
        trace_id=None,
        correlation_id=None,
        authority_boundary="cognitive_non_material_runtime_boundary",
        state_before="activation/confidence/cost",
        state_after="activation/confidence/cost",
        persistence_requirement="NOT_REQUIRED",
        recovery_requirement="NOT_REQUIRED",
        end_to_end_scenario_id=f"C09-E2E-{pi_id}",
        expected_observable_consequence=(
            "consumer_observes_pi_specific_causal_contribution"
        ),
        negative_or_mutation_probe="disable_or_zero_signal_eliminates_contribution",
    )


PI_ACCEPTANCE_MANIFEST: tuple[PIAcceptanceEntry, ...] = tuple(
    _entry(pi_id) for pi_id in FROZEN_PI_IDS
)


def evaluate_acceptance(
    manifest: tuple[PIAcceptanceEntry, ...],
    observations: tuple[AcceptanceObservation, ...],
) -> tuple[tuple[PIAcceptanceEntry, ...], AcceptanceSummary]:
    by_pi = {observation.pi_id: observation for observation in observations}
    evaluated: list[PIAcceptanceEntry] = []

    for entry in manifest:
        observation = by_pi.get(entry.pi_id)
        if observation is None:
            evaluated.append(entry)
            continue

        persistence_ok = (
            entry.persistence_requirement == "NOT_REQUIRED"
            or observation.persistence_verified is True
        )
        recovery_ok = (
            entry.recovery_requirement == "NOT_REQUIRED"
            or observation.recovery_verified is True
        )
        accepted = (
            observation.reachable
            and observation.consumed
            and observation.causal_contribution_observed
            and observation.traceable
            and observation.governed
            and persistence_ok
            and recovery_ok
            and bool(observation.trace_id)
            and bool(observation.correlation_id)
            and observation.scenario_id == entry.end_to_end_scenario_id
            and bool(observation.observable_consequence_ref)
        )
        if accepted:
            evaluated.append(
                replace(
                    entry,
                    trace_id=observation.trace_id,
                    correlation_id=observation.correlation_id,
                    acceptance_status="ACCEPTED",
                    unresolved_reason=None,
                )
            )
        else:
            evaluated.append(
                replace(
                    entry,
                    trace_id=observation.trace_id or None,
                    correlation_id=observation.correlation_id or None,
                    unresolved_reason="native_acceptance_conditions_incomplete",
                )
            )

    accepted_count = sum(item.acceptance_status == "ACCEPTED" for item in evaluated)
    persistence_gaps = sum(
        item.persistence_requirement == "REQUIRED"
        and (
            by_pi.get(item.pi_id) is None
            or by_pi[item.pi_id].persistence_verified is not True
        )
        for item in evaluated
    )
    recovery_gaps = sum(
        item.recovery_requirement == "REQUIRED"
        and (
            by_pi.get(item.pi_id) is None
            or by_pi[item.pi_id].recovery_verified is not True
        )
        for item in evaluated
    )
    summary = AcceptanceSummary(
        manifest_cardinality=len(evaluated),
        unique_pi_ids=len({item.pi_id for item in evaluated}),
        accepted_pi_count=accepted_count,
        unresolved_pi_count=len(evaluated) - accepted_count,
        untested_required_persistence=persistence_gaps,
        untested_required_recovery=recovery_gaps,
        global_end_to_end_paths_native_and_reproducible=(
            accepted_count == len(evaluated) == 36
        ),
    )
    return tuple(evaluated), summary
