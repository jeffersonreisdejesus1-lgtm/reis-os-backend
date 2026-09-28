# COMMAND-VISUAL-SYSTEM-CANDIDATE-V0.1

## Object
`COMMAND-VISUAL-SYSTEM-CANDIDATE-V0.1`

## Domain
`LYRA + ÍRIS`

## Status
`CANDIDATE_FOR_VISUAL_REVIEW`

This artifact turns the semantic design foundation into a concrete visual candidate. It is not a final brand freeze and does not authorize production implementation.

## Direction

```text
DARK-FIRST
HIGH-INFORMATION
INSTITUTIONAL
TECHNICAL
CALM
EVIDENCE-AWARE
ANDROID-FIRST
```

Dark-first is a presentation direction, not a requirement that light mode be impossible. All semantic tokens must remain themeable.

## Candidate palette

### Neutral foundation

| Token | Candidate | Purpose |
|---|---:|---|
| `surface.canvas` | `#0B0F14` | app background |
| `surface.base` | `#111827` | primary panels |
| `surface.raised` | `#18212F` | elevated cards / inspector |
| `surface.sunken` | `#0F141C` | inset regions / graph background |
| `border.default` | `#273244` | low-emphasis boundaries |
| `border.strong` | `#3A475C` | active/important boundaries |
| `text.primary` | `#F4F7FB` | primary reading |
| `text.secondary` | `#A9B4C2` | metadata / secondary labels |
| `text.tertiary` | `#7F8A99` | low-priority context |
| `text.inverse` | `#0B0F14` | text on light semantic fills |

### Brand accent candidate

| Token | Candidate | Purpose |
|---|---:|---|
| `brand.primary` | `#4CC9F0` | REIS OS active accent |
| `brand.primary.strong` | `#22B8E6` | focused emphasis |
| `brand.primary.soft` | `#153646` | accent surface |

The accent is deliberately cool/technical and should not be used for semantic success/failure states.

### Epistemic/state candidate palette

| State | Token | Candidate |
|---|---|---:|
| PASS | `state.pass` | `#2ED47A` |
| HOLD | `state.hold` | `#F6C85F` |
| DEGRADE | `state.degrade` | `#F28C28` |
| FAIL | `state.fail` | `#E25555` |
| UNKNOWN | `state.unknown` | `#7C8798` |
| STALE | `state.stale` | `#9A8FB3` |
| CONFLICT | `state.conflict` | `#B26BFF` |
| NOT_PROVEN | `state.not_proven` | `#6FA8DC` |
| NOT_AUTHORIZED | `state.not_authorized` | `#D16D9E` |
| ASSURED | `state.assured` | `#8B7CF6` |
| EVIDENCE | `state.evidence` | `#63B3ED` |

Critical rule:

```text
COLOR_ONLY_MEANING = PROHIBITED
```

Every state is represented through at least label + color + one additional channel where material (icon, border style, pattern, or temporal marker).

## Candidate typography

Primary candidate:

```text
UI / READING = IBM Plex Sans
IDENTIFIERS / HASHES / RECEIPTS / CODE = IBM Plex Mono
ANDROID FALLBACK = Roboto / system sans
MONO FALLBACK = system monospace
```

Rationale:
- technical without looking like a generic terminal;
- strong numerical/metadata legibility;
- works for dense operational interfaces;
- clear mono companion for institutional identifiers.

Typography remains candidate until visual review and accessibility testing.

## Type scale candidate

| Role | Size | Weight | Line height |
|---|---:|---:|---:|
| Display | 28 | 600 | 34 |
| H1 | 24 | 600 | 30 |
| H2 | 20 | 600 | 26 |
| H3 | 17 | 600 | 23 |
| Body | 15 | 400 | 22 |
| Body strong | 15 | 600 | 22 |
| Label | 13 | 600 | 18 |
| Metadata | 12 | 400 | 17 |
| Micro | 11 | 500 | 15 |
| Mono body | 13 | 400 | 19 |

## Spacing scale

```text
space.1 = 4
space.2 = 8
space.3 = 12
space.4 = 16
space.5 = 20
space.6 = 24
space.8 = 32
space.10 = 40
space.12 = 48
```

Base rhythm: 4dp.

## Radius candidate

```text
radius.xs = 4
radius.sm = 8
radius.md = 12
radius.lg = 16
radius.pill = 999
```

Default operational cards: `radius.md`.
Critical state panels may use stronger border emphasis rather than larger radius.

## Elevation candidate

Use elevation sparingly.

```text
elevation.0 = flat
elevation.1 = local card separation
elevation.2 = floating inspector / sheet
elevation.3 = modal / critical overlay
```

Shadows must not be required to understand hierarchy; borders and surfaces remain sufficient.

## Density modes

```text
COMFORTABLE = default mobile reading
DENSE = evidence / timeline / metric-heavy views
FOCUS = graph or object inspection
```

Density changes spacing and metadata visibility, not semantic meaning.

## Graph visual candidate

Node classes:
- OCS: strong outline + canonical label;
- component: standard outline;
- protocol/PI: compact chip-node;
- evidence object: evidence accent + document glyph;
- authority object: shield-boundary glyph;
- risk/failure mode: risk glyph + semantic state treatment.

Edge classes remain visually distinguishable by label and line treatment; visual style does not create edge semantics.

## Motion

Motion is informational only.

```text
motion.fast = 120ms
motion.standard = 180ms
motion.slow = 260ms
```

Allowed:
- panel transition;
- focus shift;
- graph drill-down continuity;
- bottom-sheet opening.

Prohibited:
- motion as sole indicator of state;
- celebratory success animation;
- attention-grabbing loops for non-critical content.

## Accessibility constraints

- all text/state combinations must meet target contrast;
- critical state labels persist under text scaling;
- minimum touch target 48dp candidate baseline;
- no hover-only behavior;
- charts and graph views require textual equivalents;
- state differentiation tested in grayscale and common color-vision deficiency simulations.

## Review questions

Lyra review:
- Does this look recognizably REIS OS rather than generic admin SaaS?
- Does the accent communicate institutional precision without marketing energy?
- Is the semantic palette coherent with authority/evidence language?

Íris review:
- Does the palette survive dense mobile layouts?
- Are semantic distinctions legible without color?
- Is typography stable under long reading sessions and metadata density?
- Does the system support graph + dashboard + timeline without fragmenting visually?

## Non-scope

`FINAL_BRAND_FREEZE = FALSE`
`FINAL_COLOR_APPROVAL = FALSE`
`FINAL_TYPEFACE_APPROVAL = FALSE`
`PRODUCTION_UI = NOT_AUTHORIZED`
