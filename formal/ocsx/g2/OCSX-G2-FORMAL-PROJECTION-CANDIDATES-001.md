# OCS-X G2 Formal Projection Candidates

OBJECT = OCSX-G2-FORMAL-PROJECTION-CANDIDATES-001
PARENT = OCSX-G2-MULTIAGENT-CONSTITUTIONAL-ARCHITECTURE-001
STATE = FORMAL_MODEL_DESIGN_ONLY
IMPLEMENTATION = NOT_AUTHORIZED

## Purpose

Define a bounded formal-verification surface for G2 control semantics while keeping LLM cognition opaque.

No claim in this document equates model checking with cognitive correctness, runtime enforcement, production readiness, or institutional assurance.

## Abstract state

```text
vars = {
  global_status,
  terminal_reason,
  agent_status[agent],
  profile_hash[agent],
  expected_profile_hash[agent],
  fencing_epoch[agent],
  active_writer[state_domain],
  writer_epoch[state_domain],
  inbox[agent],
  wait_for,
  evidence_state,
  cog_assurance_state,
  constitutional_state,
  security_state,
  constituent_state,
  founder_authorization,
  authority_refs,
  stop_epoch
}
```

Abstract enums:

```text
GlobalStatus = INIT | ACTIVE | DEGRADED | HOLD | STOPPED
AgentStatus = CREATED | BOUND | READY | RUNNING | WAITING | HOLD | STOPPED | FENCED | FAILED | REPLACED
Finding = UNKNOWN | OK | HOLD | DENY
CogAssurance = UNKNOWN | CLEAR | BLOCKING
Constituent = UNKNOWN | VALID | INVALID | REQUIRES_FOUNDER
```

## Ownership projection

`Owner(state_domain)` is static per architecture generation.

Safety:

```text
NoCrossDomainWrite ==
  forall write_event:
    write_event.agent = Owner(write_event.state_domain)
```

```text
NoStaleEpochWrite ==
  forall write_event:
    write_event.epoch = writer_epoch[write_event.state_domain]
```

If two distinct live instances claim the same domain and epoch:

```text
SplitBrainDetected => FenceBoth
```

## Identity/profile projection

Before READY/RUNNING:

```text
ProfileBound(agent) == profile_hash[agent] = expected_profile_hash[agent]
```

Violation:

```text
~ProfileBound(agent) => agent_status[agent] = FENCED
```

Identity/profile binding does not grant authority.

## Message routing projection

Each message has:
`source, destination, type, mission, profile_hash, causal_parent_ids, integrity_hash`.

Safety:

```text
AllowedRoute(source, destination, type)
```

must hold for every delivered message.

Prohibited properties:
- no direct self-assurance route;
- no untyped broadcast;
- no message creates an authority_ref;
- handoff message does not mutate authority set.

```text
NoAuthorityCreation == authority_refs' subseteq authority_refs union ExternallyValidatedAuthorityRefs
```

```text
NoHandoffAuthorityTransfer ==
  HandoffMessage => authority_refs' = authority_refs
```

## Stop projection

```text
GlobalStop == global_status = STOPPED
```

After STOP:

```text
NoPostStopReentry ==
  GlobalStop => [](~exists agent: agent_status[agent] = RUNNING)
```

```text
StopStable == GlobalStop => [](global_status = STOPPED)
```

No new writer lease may be issued after `stop_epoch`.

## No-progress / livelock projection

Material progress is an abstract predicate supplied externally to the model.

```text
NoProgressWindowExpired ==
  bounded_epochs_without(MaterialProgress)
```

Message count, retries and equivalent repeated cognition do not satisfy MaterialProgress.

Livelock candidate:

```text
StateChanges AND ~MaterialProgress for N epochs => LIVELLOCK
```

Expected response:
`HOLD or STOP` according to preregistered mission policy.

## Deadlock projection

Wait-for graph:
`wait_for[agent] subseteq Agents`.

Candidate deadlock predicate:

```text
Deadlock ==
  global_status != STOPPED
  AND every active agent is WAITING/HOLD
  AND wait_for contains a directed cycle
  AND no admissible external event can break the cycle
```

Liveness target under finite-state/fair-detection assumptions:

```text
Deadlock => <> (global_status = HOLD or global_status = STOPPED)
```

## Cognitive acceptance projection

LLM outputs are opaque values. Model only eligibility flags.

```text
CognitiveAccept ==
  synthesis_present
  AND evidence_state = OK
  AND cog_assurance_state = CLEAR
  AND ~blocking_contradiction
```

No majority-by-count rule exists.

Self-homologation prohibition:

```text
NoSelfHomologation ==
  assurance_author notin provenance_authors_of_target_cognition
```

## Action eligibility projection

```text
ActionEligible ==
  CognitiveAccept
  AND constitutional_state = OK
  AND security_state = OK
  AND authority_ref_valid
  AND evidence_state = OK
  AND global_status != STOPPED
```

Safety:

```text
NoActionWithoutEligibility == action_attempt => ActionEligible
```

No model transition executes the external effect; it models eligibility only.

## Physiology-change projection

```text
PhysiologyChangeEligible ==
  constitutional_state = OK
  AND constituent_state = VALID
  AND independent_assurance_ok
  AND founder_authorization
```

Safety:

```text
NoInternalConstituentPower ==
  ~founder_authorization => ~PhysiologyChangeEligible
```

A13 may set `REQUIRES_FOUNDER`; it may not set founder authorization.

## Degraded-mode projection

Required hard dependencies:
- A08 constitutional unavailable => action eligibility FALSE.
- A09 security unavailable => tool/effect eligibility FALSE.
- A05 synthesis unavailable => cognitive acceptance FALSE.
- A06 assurance unavailable => cognitive acceptance FALSE where independence required.

Other agent unavailability may preserve read-only or proposal-only operation as defined by architecture policy.

Safety:

```text
MissingHardDependencyNeverUpgradesClaim
```

## Recovery / replacement projection

Replacement requires:

```text
ValidReplacement ==
  predecessor_fenced
  AND l0_binding_ok
  AND profile_binding_ok
  AND authority_snapshot_ok
  AND namespace_ok
  AND checkpoint_integrity_ok
  AND stop_state_preserved
  AND new_epoch > old_epoch
```

Safety:

```text
NoReplacementWithoutFencing
EpochMonotonic
StopPreservedAcrossRecovery
```

Liveness under healthy recovery steward + storage assumptions:

```text
RecoverableFailure => <> (ReplacementReady or FENCED_STOP)
```

## Provenance projection

Evidence/provenance graph is a DAG for derivational links.

Safety:

```text
NoCircularValidation == derivation_graph has no directed cycle
```

```text
EvidenceStrengthMonotonic ==
  derived_strength <= max_strength_permitted_by_sources_and_validation
```

Counterevidence cannot be deleted by synthesis transitions.

## Technology-independence projection

Abstract critical dependency record:

```text
CriticalDependency(provider, capability, fallback_tested)
```

Invariant:

```text
CriticalAndUnsubstitutable => explicit_dependency_risk = TRUE
```

Provider selection never mutates OCS identity or authority state.

## Candidate verification suites

T0 — Ownership/Fencing
- NoCrossDomainWrite
- NoStaleEpochWrite
- SplitBrainDetectedImpliesFence

T1 — Stop/Recovery
- NoPostStopReentry
- StopStable
- EpochMonotonic
- StopPreservedAcrossRecovery

T2 — Messaging/Authority
- AllowedRoutesOnly
- NoAuthorityCreation
- NoHandoffAuthorityTransfer

T3 — Eligibility/Guardians
- NoActionWithoutEligibility
- NoInternalConstituentPower
- MissingHardDependencyNeverUpgradesClaim

T4 — Assurance/Provenance
- NoSelfHomologation
- NoCircularValidation
- EvidenceStrengthMonotonic

T5 — Deadlock/Livelock
- DeadlockEventuallyDetected
- LivelockEventuallyHeldOrStopped
- EligibleWorkEventuallyRunsOrStops under explicit fairness assumptions

## Fairness boundary

Fairness assumptions must be declared per model. No unconditional liveness claim is valid if required agents/providers/storage can remain unavailable forever.

Preferred pattern:
- weak fairness only for enabled deterministic control transitions;
- environment/provider availability represented explicitly;
- no fairness assumption over opaque cognition quality.

## Non-claims

FORMAL_PASS != LLM_CORRECTNESS
FORMAL_PASS != RUNTIME_ENFORCEMENT
FORMAL_PASS != SECURITY_CERTIFICATION
FORMAL_PASS != INSTITUTIONAL_ASSURANCE
MODEL_ELIGIBILITY != EXTERNAL_EFFECT_EXECUTION

This document authorizes no implementation, trial, merge, promotion, production routing, canonical write, OURO access, or Kernel authority mutation.
