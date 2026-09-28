# NOESIS-TO-LYRA-COMMAND-BRAND-IDENTITY-001

## Mission
Consolidate the REIS OS Command brand and visual-semantic identity from the candidate foundation already materialized in PR #68.

## Role boundary

```text
NÓESIS = orchestration / constraints / integration / baseline preparation
LYRA   = brand / naming / language / visual-semantic identity
ÍRIS   = UX/UI / interaction / accessibility / design system
```

This handoff does not transfer authority. It provides a prepared baseline for Lyra to evaluate, reject, refine, or confirm.

## Baseline already available

Read first:
- `COMMAND-BRAND-VISUAL-LANGUAGE-001.md`
- `COMMAND-DESIGN-TOKENS-SEMANTIC-CONTRACT-001.md`
- `COMMAND-VISUAL-SYSTEM-CANDIDATE-V0.1.md`
- `COMMAND-FOUNDER-EXPERIENCE-ARCHITECTURE-001.md`
- `COMMAND-HIGH-FIDELITY-WIREFRAME-SPEC-001.md`

## Product identity already constrained

```text
REIS OS COMMAND
= FOUNDER-EXCLUSIVE INSTITUTIONAL EXPERIENCE
= OPERATIONAL OBSERVATORY + CONTROL SURFACE
!= COMMERCIAL PRODUCT UX
```

The Command should feel institutional, technical, evidence-aware, controlled, high-information, and distinctive without becoming decorative or generic-dashboard-like.

## Non-negotiable semantic invariants

Lyra may change visual expression, but must preserve the semantic separations below:

```text
CURRENT != STALE
UNKNOWN != ZERO
PASS != ASSURED
REQUESTED != EXECUTED
PROPOSED != AUTHORIZED
EXECUTED != VERIFIED
VERIFIED != ASSURED
CAPABILITY != AUTHORITY
UI_DOES_NOT_CREATE_AUTHORITY
COLOR_ONLY_MEANING = PROHIBITED
```

## Candidate visual direction to review

Current candidate, not frozen:

```text
DIRECTION = DARK-FIRST / HIGH-INFORMATION / INSTITUTIONAL
BRAND_ACCENT_CANDIDATE = #4CC9F0

PASS           = #2ED47A
HOLD           = #F6C85F
DEGRADE        = #F28C28
FAIL           = #E25555
UNKNOWN        = #7C8798
CONFLICT       = #B26BFF
NOT_PROVEN     = #6FA8DC
NOT_AUTHORIZED = #D16D9E

UI_FONT_CANDIDATE   = IBM Plex Sans
MONO_FONT_CANDIDATE = IBM Plex Mono
```

## Lyra decisions required

Lyra should explicitly decide each item rather than implicitly accepting the baseline:

### 1. Brand character
Define 4–7 stable attributes for the Command.
Candidate set:
- institutional;
- precise;
- controlled;
- high-information;
- evidence-aware;
- technologically sophisticated;
- non-promotional.

Deliver:
```text
BRAND_CHARACTER = CONFIRMED | REVISED
RATIONALE = ...
```

### 2. Primary visual identity
Assess whether the cyan/blue candidate actually represents REIS OS rather than merely looking technological.

Deliver:
- primary accent;
- neutral surface family;
- light/dark relationship;
- whether dark-first remains correct;
- visual differentiation from generic developer/admin products.

### 3. Epistemic state palette
Review all semantic colors as a system, not individually.

Requirements:
- no critical state may rely on color alone;
- PASS must not visually imply assurance or promotion;
- NOT_PROVEN and UNKNOWN must be distinguishable;
- HOLD and DEGRADE must be distinguishable;
- NOT_AUTHORIZED must not look like technical failure;
- CONFLICT must not look like ordinary warning.

### 4. Typography
Review IBM Plex Sans / Mono.

Criteria:
- Android readability;
- dense operational interfaces;
- numbers/identifiers;
- institutional distinction;
- long-session comfort;
- Portuguese diacritics;
- accessibility.

Lyra may keep, replace, or define a hierarchy of UI/display/mono families.

### 5. Voice and language
Freeze a Command-specific language guide for:
- headings;
- state labels;
- alerts;
- evidence messages;
- Founder decisions;
- assurance language;
- errors;
- empty states;
- unknown/stale/conflict language.

Tone constraints:
```text
CONCISE
INSTITUTIONAL
NON-PROMOTIONAL
UNCERTAINTY_EXPLICIT
NO_FALSE_COMPLETION
NO_EMOTIONAL_MANIPULATION
```

### 6. OCS identity language
Define how the 10 OCSs are visually differentiated without creating rank/supremacy unless semantically required.

Decide:
- whether each OCS receives a stable accent;
- whether OCS color is structural, navigational, or brand-semantic;
- how colors coexist with epistemic state colors;
- rules preventing OCS identity from overriding state meaning.

### 7. Iconography
Define iconography family and rules for:
- evidence;
- authority;
- assurance;
- recovery;
- state;
- risk;
- causality;
- graph layers;
- integrations;
- OCSs.

## Deliverables expected from Lyra

```text
L1 = COMMAND_BRAND_PRINCIPLES_FINAL_CANDIDATE
L2 = COMMAND_COLOR_SYSTEM_FINAL_CANDIDATE
L3 = COMMAND_TYPOGRAPHY_FINAL_CANDIDATE
L4 = COMMAND_ICONOGRAPHY_DIRECTION
L5 = COMMAND_VOICE_AND_NAMING_GUIDE
L6 = OCS_VISUAL_IDENTITY_RULES
L7 = BRAND_TO_IRIS_HANDOFF_NOTES
```

## Acceptance criteria

Lyra's output is ready for Íris when:
- semantic states remain unambiguous;
- brand and operational state colors do not collide;
- typography is viable on Android;
- the visual identity is recognizably REIS OS rather than a generic SaaS/admin dashboard;
- naming and language are internally consistent;
- accessibility constraints are acknowledged;
- decisions identify what is frozen vs still exploratory.

## Explicit non-scope

Lyra must not:
- authorize production implementation;
- define runtime truth;
- redefine Atlas semantics;
- infer authority from UI;
- authorize PostgreSQL/L5/AI;
- merge or promote PR #68 without the proper gate.
