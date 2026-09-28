# OCS-X Outcome Classification Contract

OBJECT = OCSX-OUTCOME-CLASSIFICATION-CONTRACT-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
STATUS = FROZEN_BEFORE_TRIAL_AUTHORIZATION

## Outcomes

`Progress` — material, evidence-backed advancement toward the task's frozen completion condition. A response, token generation, narrative elaboration, or unsupported assertion is not progress by itself.

`NoProgress` — the scheduler cycle completes without material advancement and without a structural/system failure. This includes cases where admissible evidence is insufficient and the correct behavior is to preserve UNKNOWN rather than fabricate advancement.

`Fail` — the cycle cannot validly proceed because a required structural precondition, schema, dependency, authority binding, integrity check, or protocol condition fails.

## Deterministic precedence

1. If a mandatory structural/protocol precondition is invalid => `Fail`.
2. Else if at least one frozen completion-relevant state/evidence item changes validly => `Progress`.
3. Else => `NoProgress`.

No classifier may downgrade a `Fail` condition to `NoProgress` or upgrade `NoProgress` to `Progress` merely because text was produced.

## Stop binding

T2 monitor enabled + `NoProgress` => `NO_PROGRESS -> STOP`.
`Fail` => `FAIL -> STOP`.
Bound exhausted without earlier terminal condition => `BOUND_COMPLETE -> STOP`.
`Progress` must never map to `NO_PROGRESS` stop.

## Evidence

Every classification record MUST contain: task_id, cycle_id, input_hash, admissible_evidence_count, changed_completion_relevant_fields, structural_failures, outcome, stop_reason, classifier_contract_hash, record_hash.

Missing required classification evidence => `UNKNOWN`; it cannot be interpreted as Progress, NoProgress, Fail, PASS, or zero.

## Authority boundary

This contract defines pretrial semantics only. It does not instantiate OCS-X, activate L1, authorize trial execution, grant production routing, or authorize canonical state mutation.