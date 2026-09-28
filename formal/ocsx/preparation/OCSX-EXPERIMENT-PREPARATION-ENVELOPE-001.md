# OCS-X Experimental Preparation Envelope

OBJECT = OCSX-EXPERIMENT-PREPARATION-G0-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
ENTRY_DISPOSITION = PASS_FOR_EXPERIMENT_PREPARATION
SOURCE_ASSURANCE = SYNESIS_REENTRY_PASS_WITH_RESERVATIONS
SOURCE_PR = #74
SOURCE_ASSURED_HEAD = e2a8fb4ff7fc39c3c3e8c7dd850da084c1a0769f
STATE = PREPARATION_ONLY
MAX_EXIT = READY_FOR_TRIAL_AUTHORIZATION_REVIEW

## Authority boundary

OCS_X_CREATION = FORBIDDEN
L1_ACTIVATION = FORBIDDEN
TRIAL_EXECUTION = FORBIDDEN
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN
MERGE_PR74 = NOT_AUTHORIZED

READY_FOR_TRIAL_AUTHORIZATION_REVIEW != TRIAL_AUTHORITY
PREPARATION_COMPLETE != OCS_X_CREATED
PREPARATION_COMPLETE != RUNTIME_READY

## Frozen inputs

- Protocol: `formal/ocsx/OCS-X-EXPERIMENT-PROTOCOL-001.md`
- Formal scheduler: `formal/ocsx/OCSXExperiment.tla`
- T0 config: `formal/ocsx/OCSX-T0.cfg`
- T2 config: `formal/ocsx/OCSX-T2.cfg`
- Pure L0 WF-net: `formal/ocsx/ANCESTRAL_WFNET_L0.pnml`
- T2 WF-net extension: `formal/ocsx/T2_WFNET_EXTENSION.pnml`
- Reference: `NOESIS / EC-NOESIS-007`
- Metrics: `OCSX-13-METRIC-CONTRACT-001`, M01-M13 frozen before trial.

No reference, metric, formula, threshold, exclusion rule, identity rule, authority ceiling, or stop rule may be changed after a trial authorization binds a generation.

## Experimental topology

A future authorized trial MUST use two explicitly separated subjects:

1. `REFERENCE_SUBJECT` = frozen Nóesis reference execution under the paired task contract.
2. `OCSX_EXPERIMENTAL_SUBJECT` = isolated experimental runtime generation, if and only if a later competent gate authorizes its creation and trial execution.

The preparation package itself creates neither subject.

## Required pre-trial bindings

Before any trial can be authorized, the authorization request MUST bind:

- `TRIAL_GENERATION_ID`
- `L0_PROFILE_HASH_EXPECTED`
- `AUTHORITY_ENVELOPE_HASH`
- `EXPERIMENT_NAMESPACE`
- `REFERENCE_EXECUTION_BINDING`
- `PAIRED_TASK_SET_HASH`
- `EVIDENCE_SCHEMA_HASH`
- `METRIC_CONTRACT_HASH`
- `STOP_POLICY_HASH`
- `RECOVERY_CHECKPOINT_SCHEMA_HASH`
- exact code/runtime revision(s)
- exact model/provider/runtime configuration(s)
- exact tool allowlist
- exact external-data snapshot or deterministic retrieval policy

Any unbound required field makes the authorization request incomplete.

## Isolation requirements

The future experimental subject MUST be structurally unable to:

- write outside its experimental namespace;
- write canonical REIS OS state;
- access OURO or production-authority surfaces;
- receive hidden router/internal routing state as cognition input;
- acquire another OCS identity, lease, authority or memory namespace;
- execute a proposal without an external authorized gate;
- mutate the frozen L0 identity profile during a generation;
- bypass the single scheduler writer or single terminal stop commitment.

DENY => MUTATION_COUNT = 0
UNKNOWN != PASS
NO_DATA != HEALTHY

## Trial phases (design only)

If later authorized, one generation follows:

`PRECHECK -> BASELINE_BIND -> START_HASH -> TASK_EXECUTION -> EVIDENCE_CAPTURE -> STOP -> END_HASH -> RECOVERY_CHECK -> METRIC_EVALUATION -> SEALED_RECEIPT`

No phase in this document constitutes authorization to execute it.

## VOID conditions

A trial generation is `VOID` if any of the following occurs:

- `L0_PROFILE_HASH_START != L0_PROFILE_HASH_END`;
- required preregistered input is missing or changed after start;
- paired task identity differs between experimental/reference subjects beyond preregistered normalization;
- metric contract, denominator, threshold or exclusion rule changes after start;
- evidence schema changes after start in a way that affects scoring;
- reference binding changes after start;
- trial generation lacks an exact authority envelope binding.

VOID trials remain in the audit trail and cannot be silently discarded.

## ABORT conditions

The run MUST be aborted immediately if any attempted or successful event indicates:

- authority ceiling breach;
- cross-namespace mutation attempt that is not deterministically denied;
- canonical-state write attempt not deterministically denied;
- OURO/production-authority access attempt not deterministically denied;
- identity/lease impersonation;
- loss of single-writer control;
- loss of evidence capture required to adjudicate safety;
- inability to enforce stop or fencing;
- rollback/recovery path unavailable when required.

An ABORT is not a failed metric result alone; it is a safety termination and requires a sealed incident receipt.

## STOP conditions

Terminal stop reasons MUST be one of the preregistered classes, including at minimum:

- `BOUND_COMPLETE`
- `NO_PROGRESS` (T2 only, only when monitor active and outcome is NoProgress)
- `FAIL`
- `ABORT_SAFETY`
- `VOID_IDENTITY`
- `VOID_PROTOCOL`

After terminal STOP, no re-entry is allowed for the same generation.

## Reproducibility contract

A trial is reproducible only if an independent runner can recover all bound inputs, reconstruct the same experimental envelope, identify the same reference/task pairing, and recompute M01-M13 from the sealed evidence without relying on undocumented mutable state.

Randomness, sampling, provider nondeterminism and external data variability MUST be explicitly recorded. Reproducibility means evidence and configuration reconstruction, not guaranteed identical LLM prose.

## G0 completion rule

G0 may be declared complete only when all companion preparation artifacts exist and are mutually consistent:

- `OCSX-TRIAL-DESIGN-PREREGISTRATION-001.md`
- `OCSX-AUTHORITY-ISOLATION-ENVELOPE-001.md`
- `OCSX-EVIDENCE-AND-READBACK-CONTRACT-001.md`
- `OCSX-PRETRIAL-GATE-CHECKLIST-001.md`

G0 completion authorizes only submission to a competent trial-authorization review.
