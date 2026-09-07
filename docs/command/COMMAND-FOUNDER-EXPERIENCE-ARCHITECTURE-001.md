# COMMAND-FOUNDER-EXPERIENCE-ARCHITECTURE-001

## Object
`COMMAND-FOUNDER-EXPERIENCE-ARCHITECTURE-001`

## Owner domain
`ÍRIS = UX/UI / INTERACTION / ACCESSIBILITY / COMMAND FOUNDER EXPERIENCE`

## Status
`CANDIDATE_FOUNDATION`

This artifact defines the experience architecture of REIS OS Command without assuming live Atlas hydration, PostgreSQL persistence, real L5, or production UI authorization.

## Experience objective

```text
FOUNDER
→ UNDERSTAND CURRENT SITUATION
→ IDENTIFY ATTENTION
→ INSPECT OBJECT
→ READ EVIDENCE
→ DECIDE ONLY WHEN AUTHORIZED
```

The interface must optimize institutional reading, causal comprehension, risk recognition, evidence access, and Founder decision confidence.

## Primary perception model

```text
SITUAÇÃO
→ ATENÇÃO
→ OBJETO
→ EVIDÊNCIA
```

This is the default information-ordering principle across Home, operations, OCSs, gates, evidence, assurance, recovery, and future Atlas views.

## Home hierarchy

Default Home sequence:

1. `Situação atual`
2. `Mudanças relevantes`
3. `Atenção`
4. `Bloqueios`
5. `Decisões`

The Home must answer, in order:
- What is the institution doing now?
- What changed materially?
- What needs attention?
- What is blocked and why?
- Which decisions are legitimately waiting for the Founder?

## Primary navigation candidate

```text
Início
Operações
OCS
Evolução
Conversa
```

Assurance remains contextual and deep-linked rather than a mandatory sixth primary tab when the user is navigating mobile-first. Evidence, gates, recovery, readiness, and integrations can surface as domain views and object-level drill-downs.

This navigation is a candidate foundation, not a runtime routing contract.

## Command information architecture

The experience must be able to expose these institutional domains:

```text
Operations
OCS / Mission State
Instance / Recovery Center
Gates
Evidence
Assurance
Engineering Productivity
Product Quality
Refactors
Founder Approval
Release Readiness
MCP / Integrations
Evolution / Historical Trends
Physiology / Atlas
```

The mobile information architecture may group domains rather than represent every domain as a top-level tab.

## Core screen families

### 1. Home / Situation
Purpose: institutional readback.

Modules:
- current operating state;
- active missions;
- major deltas;
- attention queue;
- blocked gates;
- pending Founder decisions;
- evidence freshness summary;
- health summary.

### 2. Operations
Purpose: active mission and execution observability.

Views:
- mission list;
- mission detail;
- lifecycle/timeline;
- current responsible OCS;
- state transitions;
- holds/failures;
- receipts/evidence links.

### 3. OCS
Purpose: institutional and operational inspection of each OCS.

Views:
- identity;
- mission/function;
- capabilities vs authority;
- current instance;
- mission bindings;
- state/memory namespace references;
- recovery generation;
- evidence;
- physiology entry point.

### 4. Evolution
Purpose: longitudinal institutional understanding.

Views:
- releases;
- architectural changes;
- refactors;
- assurance history;
- failure/repair history;
- mission-performance evolution;
- institutional milestones.

### 5. Conversation
Purpose: cognitive interaction surface without conflating conversation with command authority.

Rules:

```text
ASK != COMMAND
CAN_DO != MAY_DO
REQUESTED != EXECUTED
PROPOSED != AUTHORIZED
```

No conversational affordance may imply operational authority merely because an assistant can describe or propose an action.

## Physiology / Atlas interaction model

The Atlas view is prepared now as UX architecture only.

### Structural interaction
- whole-organism overview;
- OCS drill-down;
- component drill-down;
- PI/protocol/evidence inspection;
- lateral relation traversal;
- breadcrumb/reversible navigation.

### Required graph controls
- semantic layer selector;
- relation-type filter;
- OCS filter;
- state/freshness filter;
- search;
- focus mode;
- inspect panel;
- explain-relationship action;
- evidence-link action;
- reset view.

### View layers

```text
STRUCTURAL
FUNCTIONAL
CAUSAL
AUTHORITY
OBSERVABILITY
RECOVERY
ASSURANCE
```

Layer visibility must never create an inference that the underlying relationship is proven when evidence is absent.

```text
VISIBLE_EDGE != PROVEN_CAUSALITY
EXISTENCE != CAUSAL_CONSUMPTION
OBSERVATION_FAILURE → NOT_PROVEN
```

## Object inspector pattern

Selecting any object should open a consistent inspector containing, where applicable:
- canonical identity;
- object type;
- current state;
- freshness;
- function/purpose;
- parent/children;
- relations;
- authority boundary;
- evidence refs;
- assurance status;
- risks/failure modes;
- recovery info;
- history/timeline.

## State-first UX

State is shown before action.

```text
STATE
→ CONTEXT
→ EVIDENCE
→ AVAILABLE ACTIONS
```

Critical actions must never appear before the user can see the state and the authority condition that makes the action legitimate.

## Read-only / pre-runtime discipline

Until a downstream implementation gate explicitly authorizes effects, the design must not include operational CTAs that imply executable authority.

Do not include as active product behavior:
- approve;
- merge;
- promote;
- bind;
- execute;
- recover;
- mutate canonical state.

Prototype representations may document future action placement, but must visually label them as `FUTURE / NOT ACTIVE` rather than disabled controls that could be mistaken for latent authority.

## Epistemic UI contract

Required distinctions:

```text
CURRENT != STALE
UNKNOWN != ZERO
REQUESTED != EXECUTED
EXECUTED != VERIFIED
VERIFIED != ASSURED
PROPOSED != AUTHORIZED
CAPABILITY != AUTHORITY
UI_DOES_NOT_CREATE_AUTHORITY
```

Each distinction must survive:
- Home summary;
- lists;
- detail pages;
- graph inspector;
- timeline;
- notifications;
- mobile compact mode.

## Android-first behavior

Design priorities:
- one-hand readable summaries;
- progressive disclosure;
- persistent object identity during drill-down;
- bottom-sheet inspector where suitable;
- long content in stacked sections rather than dense desktop tables;
- charts with accessible textual summaries;
- touch targets meeting accessibility guidance;
- no hover-only semantics;
- state labels remain visible in compact layouts.

## Design-system foundation

Íris should define tokens for:
- typography roles;
- spacing;
- radius;
- elevation;
- borders;
- state surfaces;
- focus;
- motion duration;
- data-density modes;
- graph node/edge classes;
- chart annotation;
- freshness;
- evidence strength.

Brand color values and typeface selection remain coordinated with Lyra; semantic token names belong to the experience system.

## Component inventory candidate

- AppShell
- TopContextBar
- BottomNavigation
- SituationSummary
- AttentionCard
- GateStateCard
- MissionCard
- OCSCard
- StateBadge
- FreshnessBadge
- EvidenceBadge
- AuthorityBoundary
- Timeline
- EvidenceList
- DecisionQueue
- MetricCard
- TrendPanel
- GraphCanvas
- GraphLayerSelector
- GraphInspector
- FilterSheet
- RecoveryPanel
- AssurancePanel
- EmptyState
- LoadingState
- ConflictState
- ErrorState

## Accessibility contract

- critical state never color-only;
- graph relationships require nonvisual textual representation;
- minimum touch target preserved;
- text scaling must not destroy state visibility;
- charts require textual reading;
- motion must not carry unique meaning;
- contrast tested for all state combinations;
- screen-reader labels use institutional nouns and current state.

## Validation targets before implementation handoff

Íris should be able to demonstrate:
- complete Founder golden path;
- Home comprehension without opening detail;
- blocked-state comprehension;
- stale/unknown/conflict differentiation;
- graph drill-down without loss of context;
- evidence discovery in <= 2 drill-downs from a material claim;
- recovery and assurance distinction;
- mobile accessibility review;
- no authority implied by visual affordance.

## Relationship with Lyra

```text
LYRA
= semantic identity / brand / language

ÍRIS
= experience architecture / interaction / accessibility / design system
```

Lyra supplies the visual-semantic grammar; Íris ensures that grammar remains usable, accessible, consistent, and structurally coherent across the Command.

## Non-scope

This artifact does not authorize:
- production UI implementation;
- live Atlas hydration;
- PostgreSQL application;
- real L5;
- ten-OCS runtime expansion;
- AI overlay;
- Founder promotion.
