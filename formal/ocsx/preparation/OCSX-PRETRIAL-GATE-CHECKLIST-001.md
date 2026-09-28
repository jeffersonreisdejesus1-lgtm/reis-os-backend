# OCS-X Pretrial Gate Checklist

OBJECT = OCSX-PRETRIAL-GATE-CHECKLIST-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
STATUS = PREPARATION_GATE
CURRENT_AUTHORITY = NO_TRIAL_AUTHORITY

A later competent reviewer may declare `READY_FOR_TRIAL_AUTHORIZATION_REVIEW` only if every REQUIRED item below is materially evidenced. Narrative assertion alone is insufficient.

## A. Provenance and frozen baseline

- [REQUIRED] exact PR/head/revision bound;
- [REQUIRED] formal spec/config/evidence hashes available;
- [REQUIRED] frozen reference = NOESIS / EC-NOESIS-007;
- [REQUIRED] frozen `OCSX-13-METRIC-CONTRACT-001` hash bound;
- [REQUIRED] preparation artifacts and hashes bound;
- [REQUIRED] no unresolved assurance blocker affecting experiment preparation.

## B. Trial design

- [REQUIRED] paired task set exists and is hashed before authorization;
- [REQUIRED] each task binds payload hash, class, evidence requirements, tools and external-data policy;
- [REQUIRED] NoProgress and Fail classification rules are frozen;
- [REQUIRED] reference/experimental normalization is frozen;
- [REQUIRED] anti-selection-bias rules are enforceable.

## C. Authority and isolation

- [REQUIRED] experimental namespace is explicit and isolated;
- [REQUIRED] tool allowlist is explicit;
- [REQUIRED] cross-namespace writes are deterministically denied;
- [REQUIRED] canonical-state writes are deterministically denied;
- [REQUIRED] OURO/production surfaces are deterministically denied;
- [REQUIRED] hidden router/internal routing state is excluded from cognitive input;
- [REQUIRED] proposal cannot self-authorize execution;
- [REQUIRED] single-writer and single-stop enforcement exists;
- [REQUIRED] stopped generation cannot re-enter;
- [REQUIRED] recovery cannot expand authority or alter L0 identity.

## D. Evidence and observability

- [REQUIRED] generation receipt schema implemented;
- [REQUIRED] event journal schema implemented;
- [REQUIRED] causal proposal/gate/execution chain observable;
- [REQUIRED] mutation-deny readback observable;
- [REQUIRED] stop/no-reentry readback observable;
- [REQUIRED] recovery readback observable;
- [REQUIRED] all M01-M13 evidence mappings implementable;
- [REQUIRED] missing evidence is represented as UNKNOWN;
- [REQUIRED] evidence sealing/content hashing implemented;
- [REQUIRED] VALID/VOID/ABORTED records all retained.

## E. Safety termination

- [REQUIRED] VOID_IDENTITY enforcement;
- [REQUIRED] VOID_PROTOCOL enforcement;
- [REQUIRED] ABORT_SAFETY enforcement;
- [REQUIRED] BOUND_COMPLETE stop;
- [REQUIRED] T2 NoProgress stop semantics;
- [REQUIRED] Fail stop semantics;
- [REQUIRED] post-stop fencing.

## F. Reproducibility

- [REQUIRED] runtime/code revision fixed;
- [REQUIRED] model/provider configuration recorded;
- [REQUIRED] tool allowlist hash recorded;
- [REQUIRED] external-data snapshot/policy recorded;
- [REQUIRED] randomness/sampling configuration recorded;
- [REQUIRED] recovery checkpoint schema fixed;
- [REQUIRED] independent evaluator can recompute metrics from sealed evidence.

## G. CI and implementation status

- [REQUIRED] exact-head checks required by the trial-authorization gate have an explicit disposition;
- `ACTION_REQUIRED/NOT_EXECUTED` is not equivalent to PASS;
- unrelated CI does not become experiment evidence merely by existing;
- runtime enforcement must be tested independently of TLA+/TLC proof.

## Gate output rules

If every REQUIRED item is proven:

`PRETRIAL_PREPARATION = COMPLETE`
`MAX_CONSEQUENCE = READY_FOR_TRIAL_AUTHORIZATION_REVIEW`

If any REQUIRED item is absent:

`PRETRIAL_PREPARATION = INCOMPLETE`
`TRIAL_AUTHORIZATION_REQUEST = NOT_READY`

In both cases:

OCS_X_CREATION = FORBIDDEN
L1_ACTIVATION = FORBIDDEN
TRIAL_EXECUTION = FORBIDDEN
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN

Only a later competent authorization artifact may alter the statuses it is explicitly empowered to alter.
