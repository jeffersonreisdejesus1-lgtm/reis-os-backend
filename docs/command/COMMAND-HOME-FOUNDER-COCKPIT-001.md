# COMMAND-HOME-FOUNDER-COCKPIT-001

## Object
`COMMAND-HOME-FOUNDER-COCKPIT-001`

## Status
`CANDIDATE_FOUNDATION`

## Purpose
Define the mobile-first Home cockpit so the Founder can understand the institution before opening any detail view.

## Primary sequence

```text
SITUAÇÃO ATUAL
→ MUDANÇAS RELEVANTES
→ ATENÇÃO
→ BLOQUEIOS
→ DECISÕES
```

## Screen contract

### 1. Situation header
Must expose:
- global operating state label;
- last material readback time;
- evidence freshness summary;
- number of active missions;
- number of open holds/blockers;
- Founder decisions pending.

The header must never collapse unknown or stale data into a reassuring global state.

### 2. Current situation
Purpose: answer `what is operating now?`

Contents:
- active mission summary;
- current primary OCS per mission;
- gate position;
- current verified state;
- current evidence freshness;
- next legitimate transition.

### 3. Material changes
Purpose: answer `what changed since my last read?`

Prioritize:
- gate transitions;
- new holds/failures;
- recovery events;
- assurance disposition changes;
- promotion/readiness changes;
- new evidence that changes a claim;
- scope or authority changes.

Do not prioritize volume of events over materiality.

### 4. Attention queue
Each item must contain:
- object identity;
- reason for attention;
- severity/risk if applicable;
- age/freshness;
- responsible domain/OCS;
- evidence availability;
- whether Founder action is actually required.

### 5. Blockers
Distinguish:

```text
TECHNICAL_BLOCKER
SEMANTIC_HOLD
ASSURANCE_HOLD
AUTHORITY_HOLD
EXTERNAL_DEPENDENCY
UNKNOWN_CAUSE
```

The UI must not use one generic red `blocked` state for all causes.

### 6. Founder decisions
Only legitimate Founder-reserved decisions appear here.

Each card includes:
- decision requested;
- exact object/head/release where applicable;
- why Founder authority is required;
- evidence/assurance status;
- consequences of approve / decline / defer;
- whether any new mutation invalidates the decision package.

```text
DECISION_QUEUE != ACTION_SUGGESTION_QUEUE
```

### 7. Institutional health strip
Candidate dimensions:
- mission health;
- evidence completeness;
- open findings;
- assurance health;
- recovery health;
- integration health;
- release readiness.

No composite score may imply promotion authority.

## Interaction rules

- tap summary → object detail;
- tap evidence count → evidence list;
- tap gate → gate history/current conditions;
- tap OCS → OCS dossier/current mission binding;
- tap blocker → causal explanation + evidence;
- tap Founder decision → decision dossier.

## Golden-path target

From Home, the Founder should be able to answer within one screen:
1. What is happening?
2. What changed?
3. What needs attention?
4. What is blocked?
5. Do I need to decide anything?

Within two drill-downs from any material claim, the Founder should reach its evidence or explicit `NOT_PROVEN` state.

## Compact mobile layout

Recommended vertical composition:

```text
[Context / freshness bar]
[Situation summary]
[Material changes carousel/list]
[Attention]
[Blockers]
[Founder decisions]
[Health / trends]
```

Horizontal carousels may be used only where they do not hide critical items. Blockers and Founder decisions should default to complete vertical visibility or an explicit count + `view all`.

## Empty-state semantics

Examples:
- No Founder decision pending → `Nenhuma decisão reservada pendente.`
- No blocker observed → `Nenhum blocker observado no readback atual.`
- No evidence available → `Evidência não disponível / NOT_PROVEN`, not an empty success state.

## Non-scope

This document does not activate live data, executable Founder actions, runtime mutations, Atlas hydration, or production UI implementation.
