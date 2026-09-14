# COMMAND-HIGH-FIDELITY-WIREFRAME-SPEC-001

## Object
`COMMAND-HIGH-FIDELITY-WIREFRAME-SPEC-001`

## Domain
`ÍRIS + LYRA`

## Status
`CANDIDATE_FOR_FIGMA_MATERIALIZATION`

This artifact specifies three first high-fidelity wireframes for later Figma materialization. It is a visual specification only.

---

# 1. HOME — FOUNDER COCKPIT

## Purpose
Answer the Founder’s first five questions without requiring drill-down:
1. What is happening now?
2. What changed?
3. What needs attention?
4. What is blocked?
5. What is waiting for my decision?

## Mobile frame

```text
┌──────────────────────────────────────┐
│ REIS OS COMMAND              CURRENT │
│ 07 Sep 2026 · 20:xx · evidence fresh│
├──────────────────────────────────────┤
│ SITUAÇÃO ATUAL                      │
│  3 missions active                  │
│  1 HOLD · 0 FAIL · 2 pending gates  │
│  Founder decisions: 1               │
│                                      │
│  [Institutional state summary]      │
├──────────────────────────────────────┤
│ MUDANÇAS RELEVANTES                 │
│ • Atlas A0 promoted/merged           │
│ • Atlas A1 candidate active          │
│ • Command visual foundation updated  │
├──────────────────────────────────────┤
│ ATENÇÃO                             │
│ [HOLD] Atlas A1 · Quality/assurance │
│ object / why / evidence / freshness │
├──────────────────────────────────────┤
│ BLOQUEIOS                           │
│ [AUTHORITY HOLD] A2 not authorized  │
├──────────────────────────────────────┤
│ DECISÕES                            │
│ Founder gate · 1 pending            │
│ evidence ready / risk / scope       │
├──────────────────────────────────────┤
│ Início  Operações  OCS  Evolução  💬│
└──────────────────────────────────────┘
```

## Composition rules
- top context bar always shows freshness/currentness;
- Situation block receives strongest visual hierarchy;
- Attention and Blockers are separate sections;
- Founder decision items never appear as generic notifications;
- percentages cannot replace state labels;
- no decorative hero artwork.

---

# 2. OCS DETAIL — INSTITUTIONAL + OPERATIONAL VIEW

## Purpose
Provide a full operational read of one OCS while preserving identity/authority distinctions.

## Mobile frame

```text
┌──────────────────────────────────────┐
│ ← OCS                              ⋮ │
│ NÓESIS                               │
│ Orchestration & routing              │
│ [ACTIVE] [GEN 4] [CURRENT]           │
├──────────────────────────────────────┤
│ MISSÃO ATUAL                         │
│ A1-ATLAS-MIN-GRAPH...                │
│ Current gate: Technical quality      │
│ Last event: CI readback               │
├──────────────────────────────────────┤
│ IDENTIDADE                           │
│ ocs_id / profile_ref / namespace     │
│ NAME != IDENTITY_PROOF               │
├──────────────────────────────────────┤
│ CAPACIDADES                          │
│ orchestration · routing · synthesis  │
├──────────────────────────────────────┤
│ AUTORIDADE                           │
│ [BOUNDARY] scope / lease / limits    │
│ CAPABILITY != AUTHORITY              │
├──────────────────────────────────────┤
│ ESTADO & RECOVERY                    │
│ instance / generation / predecessor  │
│ checkpoint / recovery / fencing      │
├──────────────────────────────────────┤
│ EVIDÊNCIA                            │
│ 12 refs · 10 current · 2 stale       │
├──────────────────────────────────────┤
│ FISIOLOGIA / ATLAS                   │
│ [Open physiology view]               │
└──────────────────────────────────────┘
```

## Interaction
- sticky OCS identity header during long scroll;
- section navigation via compact chips or jump sheet;
- identity and authority never collapsed into one section;
- evidence count links to structured evidence list;
- physiology opens Atlas focused on selected OCS.

---

# 3. ATLAS — FOCUSED MOBILE INSPECTION

## Purpose
Let the Founder move from organism structure to one object and its evidence without losing context.

## Mobile frame

```text
┌──────────────────────────────────────┐
│ ← Atlas                  Layers  ⌕   │
│ STRUCTURAL · OCS:NÓESIS              │
├──────────────────────────────────────┤
│                                      │
│       [REIS OS]                      │
│          │                           │
│       COMPOSES                       │
│          │                           │
│       [NÓESIS]                       │
│       /   |   \                      │
│ [Mission][PI][Evidence]              │
│                                      │
│  pinch / pan / tap                   │
│                                      │
├──────────────────────────────────────┤
│ SELECTED: NÓESIS                     │
│ [ACTIVE] [CURRENT]                   │
│                                      │
│ Identity                             │
│ Function                             │
│ Relations (4)                        │
│ Authority boundary                   │
│ Evidence (12)                        │
│ Assurance                            │
│ Recovery                             │
│ History                              │
│                                      │
│ [Open full inspector]                │
└──────────────────────────────────────┘
```

## Atlas interaction rules
- single tap selects object;
- second tap or inspector action opens full detail;
- layer selector changes presentation layer, not underlying graph identity;
- relation type always text-labelled;
- hidden intermediate nodes never imply transitive semantic edges;
- focus mode dims unrelated nodes but does not delete them from the conceptual model;
- selected object identity persists through inspector expansion;
- evidence is reachable in at most two drill-downs from a material claim.

## Bottom-sheet inspector states

```text
PEEK      = identity + state + function
HALF      = relations + authority + evidence summary
FULL      = complete object inspector
```

## Graph empty/error states

`NO_RELATIONS` != `NOT_LOADED`

`NOT_LOADED` != `UNKNOWN`

`OBSERVATION_FAILURE` -> `NOT_PROVEN`

The interface must label each case explicitly.

---

# 4. Shared visual hierarchy

Across all three wireframes:

```text
LEVEL 1 = current state / primary object
LEVEL 2 = attention / gate / authority
LEVEL 3 = evidence / causal explanation
LEVEL 4 = metadata / ids / freshness
```

Do not reverse this hierarchy merely because metadata is plentiful.

# 5. Figma-ready frame list

Candidate first frame set:

```text
M01_HOME_DEFAULT
M02_HOME_HOLD
M03_HOME_STALE_DATA
M04_OCS_DETAIL_ACTIVE
M05_OCS_DETAIL_RECOVERY
M06_OCS_DETAIL_CONFLICT
M07_ATLAS_OVERVIEW
M08_ATLAS_OCS_FOCUS
M09_ATLAS_OBJECT_INSPECTOR
M10_ATLAS_NOT_PROVEN
```

Each frame should have:
- normal state;
- at least one epistemic edge case;
- accessibility annotations;
- token/component references;
- no operational action wired unless separately authorized.

# 6. Exit condition for this spec

Ready for visual tool materialization when:
- visual candidate accepted for prototyping;
- typography/palette are usable as candidate tokens;
- Home/OCS/Atlas anatomy stable enough to avoid structural redraw;
- no runtime assumption required.

`FIGMA_MATERIALIZATION = NEXT_ALLOWED_DESIGN_STEP`
`PRODUCTION_IMPLEMENTATION = NOT_AUTHORIZED`
