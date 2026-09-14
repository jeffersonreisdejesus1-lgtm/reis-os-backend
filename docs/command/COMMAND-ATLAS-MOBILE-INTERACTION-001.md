# COMMAND-ATLAS-MOBILE-INTERACTION-001

## Object
`COMMAND-ATLAS-MOBILE-INTERACTION-001`

## Status
`CANDIDATE_FOUNDATION`

## Purpose
Define the mobile interaction model for the Physiological Atlas without assuming live graph hydration or production implementation.

## Primary user objective

The Founder must be able to move from organism-level orientation to evidence-backed object inspection without losing context.

```text
ORGANISM
→ OCS
→ COMPONENT
→ RELATION
→ EVIDENCE / STATE / AUTHORITY / HISTORY
```

## Entry points

Atlas may be entered from:
- OCS dossier;
- mission object;
- gate/evidence relation;
- dedicated Physiology/Atlas view;
- contextual deep link from a material claim.

The view must preserve the originating object and allow return without losing prior navigation state.

## Mobile layout

Default composition:

```text
[Context bar]
[Layer + filter controls]
[Graph viewport]
[Selection summary]
[Bottom-sheet inspector]
```

The graph viewport remains primary, but every selected relationship must have an equivalent textual representation in the inspector.

## Layer selector

Supported conceptual layers:

```text
STRUCTURAL
FUNCTIONAL
CAUSAL
AUTHORITY
OBSERVABILITY
RECOVERY
ASSURANCE
```

Rules:
- only one primary semantic layer active by default;
- optional secondary overlays must be explicitly named;
- overlay presence cannot upgrade proof state;
- hidden layers remain discoverable through a clear selector;
- layer changes preserve selected object where possible.

## Zoom model

```text
L0 = REIS OS organism
L1 = OCS
L2 = component
L3 = subcomponent / PI / protocol / evidence object
```

Zoom is presentation only.

```text
ZOOM_TRANSITIVITY = DENY
IMPLICIT_EDGE_MATERIALIZATION = DENY
```

Collapsing intermediates must not create a new semantic edge or change causal meaning.

## Node interaction

Single tap:
- select node;
- highlight direct visible relations;
- open compact selection summary.

Inspector expand:
- canonical identity;
- type;
- function;
- current state;
- freshness;
- parent/children;
- authority boundary;
- evidence refs;
- assurance state;
- recovery state;
- history.

Long press must not be required for critical access.

## Edge interaction

Selecting an edge must show:
- canonical relation type;
- source;
- target;
- definition vs observation distinction;
- proof/evidence state;
- freshness if observed;
- governing rule/thesis reference where applicable;
- contradiction/conflict state where applicable.

```text
VISIBLE_EDGE != PROVEN_CAUSALITY
EVIDENCE_POINTER != OBSERVED_EVIDENCE
```

## Relation filters

At minimum:
- `COMPOSES`
- `REQUIRES`
- `GOVERNED_BY`
- `EVIDENCED_BY`

Unknown edge types are not silently rendered as generic relationships.

## Search

Search targets:
- OCS name;
- component name;
- canonical id;
- protocol/PI;
- gate;
- evidence id/ref;
- mission id.

Search result selection centers the object and preserves active layer/filter context.

## Focus mode

Focus mode isolates:
- selected node;
- direct neighbors;
- optionally one additional hop when explicitly requested.

The UI must show that hidden graph content still exists.

## Explain relationship

`Explain relationship` opens a structured explanation containing:
- relation type;
- why it exists;
- definition source;
- evidence state;
- current applicability;
- conflicts/holds;
- whether the relationship is structural, declared causal, or observed causal.

No free-form explanation may override canonical relation/evidence state.

## Evidence drill-down

From any material relation, the Founder should reach:
- evidence pointer;
- observed evidence if available;
- freshness;
- provenance/source;
- assurance interpretation;
- `NOT_PROVEN` when evidence is unavailable or invalid.

Target: no more than two explicit drill-downs from relation selection.

## Authority overlay

Authority layer must distinguish:
- capability;
- available authority;
- reserved Founder authority;
- denied/out-of-scope authority;
- authority source/lease where available.

```text
CAPABILITY != AUTHORITY
UI_DOES_NOT_CREATE_AUTHORITY
```

## Recovery overlay

Recovery view may expose:
- generation;
- predecessor/current instance;
- checkpoint/ref;
- replacement/recovery state;
- fencing/revocation state where applicable.

It must not imply that a recovery claim is verified without readback evidence.

## Assurance overlay

Assurance state must distinguish:
- not assessed;
- assessment pending;
- PASS;
- HOLD;
- finding open;
- invalidated by mutation/new head where applicable.

Assurance is attached to an exact object/version/head when required.

## Gestures and accessibility

- pinch zoom optional, never required;
- explicit +/- zoom controls available;
- no hover dependency;
- graph has textual list alternative;
- focus order follows selected object → relations → inspector actions;
- selected node/edge announced to screen readers;
- relation type and proof state exposed as text;
- motion reduction supported.

## Non-scope

No live graph engine, database choice, hydration, causal inference, runtime event graph, production implementation, or downstream Atlas gate is authorized by this artifact.
