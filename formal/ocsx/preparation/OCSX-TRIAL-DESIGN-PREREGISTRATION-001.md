# OCS-X Trial Design Preregistration

OBJECT = OCSX-TRIAL-DESIGN-PREREGISTRATION-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
STATUS = FROZEN_BEFORE_TRIAL_AUTHORIZATION
EXECUTION_STATUS = NOT_AUTHORIZED

## Purpose

Define the future comparative trial structure before any OCS-X runtime generation exists, preventing post-outcome changes to comparison logic.

## Reference

REFERENCE_OCS = NOESIS
REFERENCE_ORGANISM = EC-NOESIS-007
REFERENCE_CHANGE_AFTER_AUTHORIZATION = FORBIDDEN

## Paired-task design

The future trial MUST use a frozen paired task set executed against the reference and experimental subjects under the same task identity and the same preregistered normalization rules.

Each task record MUST bind:

- `TASK_ID`
- `TASK_PAYLOAD_HASH`
- `TASK_CLASS`
- `EXPECTED_REQUIRED_EVIDENCE_FIELDS`
- `ALLOWED_TOOLS`
- `EXTERNAL_DATA_POLICY`
- `TIME_BUDGET_POLICY`
- `STOP_BUDGET_POLICY`
- `REFERENCE_VARIANT_ID`
- `EXPERIMENT_VARIANT_ID`

The paired task set itself MUST be hashed before trial authorization. Task substitution after the first execution of a generation is forbidden.

## Ablation structure

T0 and T2 are formal/preparatory treatment definitions:

- T0 = pure L0 scheduler shell, progress monitor disabled.
- T2 = same L0 baseline plus progress-monitor extension.

A future cognitive trial MUST NOT infer causal superiority merely from TLC differences. Formal scheduler evidence and cognitive outcome evidence remain separate.

## Outcome handling

Abstract scheduler outcomes are:

- `Progress`
- `NoProgress`
- `Fail`

Progress cannot be relabeled as NoProgress after observation. NoProgress classification rules MUST be fixed before trial authorization. Fail classification rules MUST also be fixed before trial authorization.

## Metric binding

All evaluations use `OCSX-13-METRIC-CONTRACT-001` without modification.

- Safety/technical: M01-M10, M13.
- Comparative output: M11-M12.

Missing evidence = UNKNOWN.
UNKNOWN cannot be converted to zero, PASS or exclusion.

## Generation accounting

Every authorized generation MUST end in exactly one of:

- VALID
- VOID
- ABORTED

All three are counted and retained in the audit ledger. Only VALID generations may contribute to M11/M12 denominators. VOID and ABORTED generations require explicit reason codes and evidence receipts.

## Anti-bias rules

Forbidden after first trial-generation start:

- replacing the reference;
- replacing tasks because results are unfavorable;
- changing metric thresholds;
- changing denominators;
- changing evidence requirements;
- suppressing valid adverse outcomes;
- deleting VOID/ABORT records;
- selecting only favorable seeds, provider responses or recovery attempts.

## Readiness consequence

This preregistration is preparation evidence only.
TRIAL_DESIGN_FROZEN = TRUE
TRIAL_AUTHORITY = NOT_GRANTED
