# LYRA-COMMAND-BRAND-DECISION-MATRIX-001

## Purpose
Convert the Nóesis-prepared Command brand candidate into an explicit Lyra decision package.

This document is not a final brand approval. It is the domain worklist Lyra must evaluate, revise, accept, or reject.

## Input baseline

Use these candidate inputs from PR #68:
- `COMMAND-BRAND-VISUAL-LANGUAGE-001`
- `COMMAND-DESIGN-TOKENS-SEMANTIC-CONTRACT-001`
- `COMMAND-VISUAL-SYSTEM-CANDIDATE-V0.1`
- `COMMAND-HOME-FOUNDER-COCKPIT-001`
- `COMMAND-CORE-COMPONENT-ANATOMY-001`
- `COMMAND-HIGH-FIDELITY-WIREFRAME-SPEC-001`

## Frozen institutional constraints

Lyra must not change these without explicit architectural/governance reopen:

```text
REIS OS COMMAND = FOUNDER-EXCLUSIVE INSTITUTIONAL EXPERIENCE
COMMAND = PROJECTION / CONTROL SURFACE
UI_DOES_NOT_CREATE_AUTHORITY
CAPABILITY != AUTHORITY
REQUESTED != EXECUTED
PROPOSED != AUTHORIZED
EXECUTED != VERIFIED
VERIFIED != ASSURED
UNKNOWN != ZERO
STALE != CURRENT
```

## Decision matrix

| Domain | Candidate | Lyra must decide | Acceptance condition |
|---|---|---|---|
| Brand character | technical + institutional + controlled + high-information | confirm / revise | description is specific enough to guide visual and verbal decisions |
| Primary tone | concise, institutional, non-promotional, evidence-aware | confirm / revise | sample language remains coherent across PASS/HOLD/UNKNOWN/NOT_AUTHORIZED |
| Dark-first direction | dark-first control-surface | accept / reject / modify | supports long operational sessions and state discrimination |
| Accent color | `#4CC9F0` candidate | confirm / replace | distinct from epistemic state colors and accessible |
| PASS | `#2ED47A` candidate | confirm / replace | not confused with authority or promotion |
| HOLD | `#F6C85F` candidate | confirm / replace | materially distinguishable from DEGRADE and UNKNOWN |
| DEGRADE | `#F28C28` candidate | confirm / replace | distinct from HOLD/FAIL |
| FAIL | `#E25555` candidate | confirm / replace | strong but not visually identical to destructive action |
| UNKNOWN | `#7C8798` candidate | confirm / replace | does not read as zero/neutral success |
| CONFLICT | `#B26BFF` candidate | confirm / replace | distinct from informational/accent |
| NOT_PROVEN | `#6FA8DC` candidate | confirm / replace | not confused with PASS or UNKNOWN |
| NOT_AUTHORIZED | `#D16D9E` candidate | confirm / replace | communicates boundary, not failure |
| UI typeface | IBM Plex Sans candidate | confirm / replace | high-density readability + Android suitability |
| Mono typeface | IBM Plex Mono candidate | confirm / replace | identifiers, hashes, receipts, technical metadata remain legible |
| OCS identity system | shared organism + differentiated OCS identity | define | 10 OCSs distinguishable without fragmenting master brand |
| Iconography | functional institutional icon family | define direction | icons never carry critical meaning alone |
| Trust cues | evidence/freshness/authority boundary visibility | confirm | trust cues cannot imply assurance or authority by aesthetics |
| Naming | canonical nouns preferred | confirm exceptions | replacements only where readability improves without semantic loss |

## OCS visual identity decision

Lyra must choose one of these strategies or define a better one:

### Strategy A — Shared master brand + OCS accent
- one REIS OS visual grammar;
- OCS-specific accent per identity;
- state colors remain global and never overwritten by OCS color.

### Strategy B — Shared master brand + OCS symbol
- global palette remains dominant;
- each OCS gets a symbol/glyph + label;
- color remains secondary.

### Strategy C — Hybrid
- shared master palette;
- OCS symbol + restrained accent;
- accessibility fallback always label/symbol based.

Lyra must explicitly prohibit any OCS identity strategy that makes epistemic state ambiguous.

## Required brand outputs

Lyra should return a domain-owned package containing:

```text
BRAND_CHARACTER
VISUAL_DIRECTION
COLOR_SYSTEM_V1_CANDIDATE
TYPOGRAPHY_SYSTEM_V1_CANDIDATE
ICONOGRAPHY_DIRECTION
OCS_IDENTITY_STRATEGY
VOICE_AND_LANGUAGE_RULES
TRUST_AND_AUTHORITY_CUES
DO_NOT_USE_RULES
OPEN_BRAND_QUESTIONS
```

## Minimum decision examples

Lyra must show the chosen system on at least these cases:
- PASS mission card;
- HOLD gate card;
- UNKNOWN evidence state;
- NOT_AUTHORIZED action boundary;
- CONFLICT object state;
- stale OCS data;
- Founder approval pending;
- Atlas relation NOT_PROVEN.

## Stop conditions

Lyra must return HOLD rather than inventing a final answer if:
- state colors cannot remain accessible;
- OCS identity conflicts with epistemic semantics;
- typography fails dense Android reading;
- the visual language starts implying authority/assurance;
- the brand becomes indistinguishable from a generic SaaS dashboard.

## Exit states

```text
LYRA_BRAND_REVIEW = PASS_CANDIDATE | PASS_WITH_REVISIONS | HOLD
FINAL_BRAND_FREEZE = FALSE unless explicitly promoted later
```

No Lyra output from this matrix authorizes production implementation.