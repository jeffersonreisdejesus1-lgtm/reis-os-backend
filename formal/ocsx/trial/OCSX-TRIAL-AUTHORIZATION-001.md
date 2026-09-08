# OCS-X Controlled Trial Authorization

OBJECT = OCSX-TRIAL-AUTHORIZATION-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
AUTHORITY = FOUNDER
DECISION = APPROVED
SCOPE = CONTROLLED_TRIAL_ONLY

## Preconditions satisfied

- PRETRIAL_PREPARATION = ASSURED_PASS
- INDEPENDENT_GEMINI_PRETRIAL_ASSURANCE = PASS
- READY_FOR_TRIAL_AUTHORIZATION_REVIEW = TRUE
- MATERIAL_BLOCKERS = NONE

## Authorization consequence

The Founder authorizes one bounded OCS-X comparative trial generation series under the frozen preregistration, paired taskset, metric contract, authority/isolation envelope, outcome classification contract and evidence/readback contract already materialized on this lineage.

Authorized:
- instantiate experimental OCS-X trial generation(s) only inside the isolated experimental namespace;
- execute the frozen paired taskset against the frozen reference NOESIS / EC-NOESIS-007 and OCS-X experimental subject;
- exercise T0/T2 pre-registered treatment semantics where applicable;
- collect and seal M01-M13 evidence according to the frozen contract;
- produce trial receipts and a trial evidence package for independent final assurance.

Not authorized:
- production routing;
- canonical REIS OS state writes;
- OURO access;
- authority expansion;
- mutation of Kernel authority;
- cross-OCS namespace writes;
- changing the frozen reference, taskset, metric thresholds, denominators, evidence requirements, or outcome semantics;
- adoption or promotion of OCS-X;
- merge of PR #74 merely because trial is authorized;
- treating trial execution as final assurance.

## Runtime equality / anti-bias

Both reference and experimental sides MUST use the same provider/model family, decoding controls, task order, external-data policy and tool allowlist except for the explicitly tested physiological treatment difference.

No post-result task substitution, denominator change, evidence suppression, selective retry, favorable-seed selection or provider-response cherry-picking is permitted.

## Fail-closed rules

- missing required runtime binding => HOLD / NO_EXECUTION;
- L0 identity mismatch => VOID_IDENTITY;
- authority-envelope mismatch => VOID_PROTOCOL;
- cross-namespace or forbidden surface mutation => ABORT_SAFETY;
- missing required evidence => UNKNOWN;
- UNKNOWN != ZERO;
- NO_DATA != HEALTHY.

## Trial authority boundary

TRIAL_AUTHORITY = GRANTED_FOR_CONTROLLED_EXPERIMENT
OCS_X_EXPERIMENTAL_GENERATION = AUTHORIZED
PRODUCTION_AUTHORITY = NOT_GRANTED
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN
PROMOTION = FORBIDDEN
MERGE_AUTHORIZATION = FALSE

After execution, the complete sealed evidence package MUST go to independent assurance before any adoption/promotion Founder Gate can be opened.
