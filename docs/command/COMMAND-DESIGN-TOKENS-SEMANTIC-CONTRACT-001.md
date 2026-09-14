# COMMAND-DESIGN-TOKENS-SEMANTIC-CONTRACT-001

## Object
`COMMAND-DESIGN-TOKENS-SEMANTIC-CONTRACT-001`

## Status
`CANDIDATE_FOUNDATION`

## Purpose
Define semantic token roles before selecting final visual values. Tokens encode meaning and usage; they do not create authority or truth.

## Token layers

```text
FOUNDATION TOKENS
→ SEMANTIC TOKENS
→ COMPONENT TOKENS
→ INSTANCE OVERRIDES (restricted)
```

### Foundation tokens
- spacing scale
- typography scale
- radius scale
- elevation scale
- motion duration scale
- border widths
- opacity levels
- data-density scale

### Semantic tokens

#### Surface
- `surface.canvas`
- `surface.primary`
- `surface.secondary`
- `surface.raised`
- `surface.overlay`
- `surface.interactive`

#### Text
- `text.primary`
- `text.secondary`
- `text.muted`
- `text.inverse`
- `text.code`
- `text.link`

#### Epistemic state
- `state.pass`
- `state.hold`
- `state.degrade`
- `state.not_proven`
- `state.not_authorized`
- `state.unknown`
- `state.stale`
- `state.conflict`
- `state.current`

#### Lifecycle
- `lifecycle.proposed`
- `lifecycle.authorized`
- `lifecycle.executed`
- `lifecycle.verified`
- `lifecycle.assured`

#### Evidence
- `evidence.pointer`
- `evidence.observed`
- `evidence.missing`
- `evidence.stale`
- `evidence.conflicting`

#### Authority
- `authority.available`
- `authority.reserved`
- `authority.denied`
- `authority.out_of_scope`

#### Risk
- `risk.low`
- `risk.medium`
- `risk.high`
- `risk.critical`

#### Freshness
- `freshness.live`
- `freshness.recent`
- `freshness.aging`
- `freshness.stale`
- `freshness.unknown`

## Mandatory semantic rules

```text
COLOR_TOKEN != MEANING_ALONE
TOKEN_NAME > RAW_COLOR_NAME
PASS != CURRENT
HOLD != FAILURE
NOT_PROVEN != NEGATIVE_PROOF
NOT_AUTHORIZED != UNAVAILABLE
STALE != UNKNOWN
VERIFIED != ASSURED
```

Raw palette names such as `green-500`, `red-600`, `blue-300` may exist only in foundation implementation. Product components consume semantic names.

## Component token examples

### StateBadge
- `stateBadge.background.<state>`
- `stateBadge.border.<state>`
- `stateBadge.text.<state>`
- `stateBadge.icon.<state>`

### AttentionCard
- `attentionCard.background`
- `attentionCard.border`
- `attentionCard.title`
- `attentionCard.meta`

### Graph
- `graph.node.surface.<class>`
- `graph.node.border.<state>`
- `graph.edge.stroke.<relation>`
- `graph.edge.pattern.<proof_state>`
- `graph.focus.ring`
- `graph.selection.surface`

### Evidence
- `evidenceBadge.pointer`
- `evidenceBadge.observed`
- `evidenceBadge.missing`

## Density modes

```text
COMFORTABLE
COMPACT
DENSE
```

Android default: `COMFORTABLE` for primary navigation and `COMPACT` for operational lists. `DENSE` is allowed only where readability remains validated and state labels do not collapse.

## Typography roles

- `display` — rare institutional headline
- `title.large`
- `title.medium`
- `title.small`
- `body.primary`
- `body.secondary`
- `label.primary`
- `label.metadata`
- `numeric.metric`
- `mono.identifier`
- `mono.evidence`

Typography must support tabular numerals for metrics and identifiers where alignment matters.

## Motion semantics

Allowed purposes:
- continuity during drill-down;
- focus transition;
- state change acknowledgment;
- expanding/collapsing context.

Prohibited:
- motion as sole status signal;
- decorative looping animation in operational views;
- animation that masks stale/unknown state.

## Accessibility

Every semantic token pair must be contrast-tested in:
- normal text;
- large text;
- state badges;
- selected/focused controls;
- graph nodes and edges;
- dark/light appearance if both are supported.

## Non-scope

No final color values, font families, implementation code, runtime wiring, or production promotion are authorized by this artifact.
