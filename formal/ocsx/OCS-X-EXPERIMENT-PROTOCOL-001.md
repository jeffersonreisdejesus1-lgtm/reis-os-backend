# OCS-X Experimental Physiology Protocol

OBJECT = OCS-X-EXPERIMENT-PROTOCOL-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
REPAIR_SOURCE = OCSX-SYNESIS-ASSURANCE-REPAIR-001
STATE = EXPERIMENT_PREPARATION_ONLY

## Institutional boundary

OCS_X_CREATION = FORBIDDEN
L1_ACTIVATION = FORBIDDEN
TRIAL_EXECUTION = FORBIDDEN
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN

This package prepares evidence for independent re-entry only. It does not instantiate an OCS identity and does not authorize runtime.

## Layer separation

T0 = PURE_L0_SCHEDULER_SHELL
T2 = L0 + PROGRESS_MONITOR_EXTENSION

L1 MAY MODIFY MECHANISM
L1 MUST NOT MODIFY IDENTITY

L0_PROFILE_HASH_START != L0_PROFILE_HASH_END -> TRIAL = VOID

## Formal package

- `OCSXExperiment.tla` — bounded abstract scheduler state machine.
- `OCSX-T0.cfg` — pure L0 model with Progress Monitor disabled.
- `OCSX-T2.cfg` — T2 model with Progress Monitor enabled.
- `ANCESTRAL_WFNET_L0.pnml` — ancestral WF-net, pure L0.
- `T2_WFNET_EXTENSION.pnml` — isolated Progress Monitor extension.
- `REFERENCE_OCS_PREREGISTRATION.md` — frozen reference selection.
- `OCSX_13_METRIC_PREREGISTRATION.md` — frozen 13-metric contract.

## Epistemic boundary

TLA+/TLC -> ABSTRACT_SCHEDULER_PROPERTIES_ONLY
WF_NET -> STRUCTURAL_CYCLE_PROPERTIES_ONLY
EVAL -> COGNITIVE_OUTPUT_QUALITY_ONLY

TLC_PASS != LLM_CORRECTNESS
FORMAL_PASS != RUNTIME_ENFORCEMENT
FORMAL_PASS != OCS_X_CREATION_AUTHORITY
FORMAL_PASS != TRIAL_AUTHORITY

## Re-entry requirement

DÉDALA may return to SÝNESIS only with:
1. exact TLA+ spec + cfg + TLC output + hashes;
2. pure L0 ancestral WF-net with independent structural check evidence;
3. frozen reference OCS;
4. frozen 13-metric contract.

Even a successful re-entry can at most justify PASS_FOR_EXPERIMENT_PREPARATION. Later creation/runtime/trial gates remain separate.
