# COMMAND-CORE-COMPONENT-ANATOMY-001

## Object
`COMMAND-CORE-COMPONENT-ANATOMY-001`

## Domain
`ÍRIS + LYRA`

## Status
`CANDIDATE_FOUNDATION`

This artifact defines the visual and semantic anatomy of core Command components. It does not authorize production implementation.

## Universal component rule

Every material component must answer at least one of:
- what is the state?
- what needs attention?
- what object is this?
- what evidence supports the claim?
- what authority boundary applies?
- what changed?

Decorative components with no operational role are out of scope.

## StateBadge

Required anatomy:
- canonical state label;
- semantic color token;
- icon or shape cue where critical;
- optional freshness suffix;
- accessible spoken label.

Examples:
- `PASS`
- `HOLD`
- `NOT PROVEN`
- `NOT AUTHORIZED`
- `STALE · 14m`

Never shorten states into ambiguous glyph-only indicators.

## SituationSummary

Anatomy:
1. institutional state headline;
2. timestamp/freshness;
3. active mission count;
4. material blockers count;
5. Founder decisions pending;
6. evidence completeness hint;
7. drill-down affordance.

The component must remain readable without charts.

## AttentionCard

Anatomy:
- severity/state;
- object identity;
- one-line causal explanation;
- owner/responsible domain;
- freshness;
- evidence count;
- action availability state (`NO_ACTION`, `REVIEW`, `FOUNDER_DECISION`, `FUTURE_NOT_ACTIVE`).

The card must distinguish:
- technical failure;
- semantic hold;
- assurance hold;
- authority hold;
- external dependency.

## GateStateCard

Anatomy:
- gate name;
- gate class;
- status;
- evidence requirement;
- current evidence state;
- authority required;
- blockers;
- next legitimate transition.

Invariant:

```text
ELIGIBLE != APPROVED
APPROVED != EXECUTED
```

## MissionCard

Anatomy:
- mission id/title;
- active OCS;
- lifecycle state;
- current gate;
- progress expressed as verified milestones, not decorative percentage only;
- last material event;
- open blocker count;
- evidence/freshness.

## OCSCard

Anatomy:
- canonical OCS name;
- specialization;
- current operational state;
- active instance/generation;
- current mission;
- authority summary;
- recovery status;
- evidence freshness;
- entry to physiology/Atlas.

Important:

```text
NAME != IDENTITY_PROOF
CAPABILITY != AUTHORITY
```

## EvidenceBadge / EvidenceList

EvidenceBadge:
- evidence count;
- freshness;
- completeness class.

EvidenceList item:
- evidence type;
- source role;
- observed at;
- integrity/reference id;
- claim supported;
- validity/assurance state.

## AuthorityBoundary

Anatomy:
- source of authority;
- scope;
- actor/OCS;
- allowed class;
- prohibited class;
- expiry/revocation/fencing if applicable.

Must be visually different from a capability indicator.

## Timeline

Each timeline event shows:
- timestamp;
- event type;
- object;
- previous state;
- resulting state;
- evidence/receipt;
- actor/source;
- whether the transition is requested, executed, verified, or assured.

No visual line may imply causality where only chronology is known.

## DecisionQueue

Each item:
- decision title;
- object;
- reason decision is reserved;
- current gate;
- evidence completeness;
- risk if approved;
- risk if deferred;
- required authority;
- state of recommendation (if any);
- action placeholder only when implementation becomes authorized.

## GraphInspector

Sections:
1. Identity
2. State
3. Function
4. Relations
5. Authority
6. Evidence
7. Assurance
8. Risk / failure modes
9. Recovery
10. History

Inspector must preserve selected-object identity while traversing relations.

## MetricCard

Anatomy:
- metric name;
- value;
- measurement window;
- source;
- completeness;
- freshness;
- direction/trend;
- anti-Goodhart context when relevant.

No metric may visually imply promotion readiness by itself.

## RecoveryPanel

Anatomy:
- current generation;
- predecessor;
- checkpoint/readback state;
- replacement status;
- recovery claim;
- evidence supporting recovery;
- fencing/revocation state;
- next legitimate operation.

## AssurancePanel

Anatomy:
- assurance object;
- assessor role;
- independence state;
- disposition;
- findings;
- assured head/version;
- scope limits;
- invalidation condition;
- relationship to Founder gate.

## Empty / Loading / Error / Conflict

### Empty
Explain whether empty means:
- zero;
- none observed;
- not yet loaded;
- unavailable;
- not applicable.

### Loading
Never erase last-known state without marking it stale/currentness unknown.

### Error
Show:
- operation that failed;
- affected scope;
- whether canonical state remains known;
- retry/readback availability.

### Conflict
Show both conflicting sources where possible; do not collapse to arbitrary winner.

## Cross-component accessibility

- state labels always textual;
- touch target >= candidate 48dp;
- focus order follows `SITUAÇÃO → ATENÇÃO → OBJETO → EVIDÊNCIA`;
- dynamic updates announced without excessive interruption;
- charts and graph components expose structured textual alternatives;
- mono identifiers remain selectable/copyable when implementation exists.

## Non-scope

`COMPONENT_CODE = NOT_AUTHORIZED`
`FINAL_VISUAL_FREEZE = FALSE`
