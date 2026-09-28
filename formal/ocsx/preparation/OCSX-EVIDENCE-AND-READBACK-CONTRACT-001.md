# OCS-X Evidence and Readback Contract

OBJECT = OCSX-EVIDENCE-AND-READBACK-CONTRACT-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
STATUS = FROZEN_BEFORE_TRIAL_AUTHORIZATION

## Evidence rule

EXECUTION != EVIDENCE
EVIDENCE != ASSURANCE
UNKNOWN != ZERO
NO_DATA != HEALTHY

Every future authorized generation MUST produce a sealed evidence set sufficient for an independent evaluator to recompute all applicable M01-M13 results.

## Required generation receipt fields

- `TRIAL_GENERATION_ID`
- `AUTHORIZATION_ARTIFACT_ID`
- `AUTHORIZATION_HASH`
- `STARTED_AT`
- `STOPPED_AT`
- `TERMINAL_CLASS`
- `STOP_REASON`
- `REFERENCE_BINDING`
- `PAIRED_TASK_SET_HASH`
- `TASK_ID`
- `TASK_PAYLOAD_HASH`
- `L0_PROFILE_HASH_START`
- `L0_PROFILE_HASH_END`
- `AUTHORITY_ENVELOPE_HASH`
- `EXPERIMENT_NAMESPACE`
- `RUNTIME_REVISION`
- `MODEL_PROVIDER_CONFIGURATION`
- `TOOL_ALLOWLIST_HASH`
- `EXTERNAL_DATA_POLICY_HASH`
- `EVIDENCE_SCHEMA_HASH`
- `METRIC_CONTRACT_HASH`
- `RECOVERY_CHECKPOINT_HASHES`
- `EVENT_JOURNAL_HASH`
- `OUTPUT_HASH`
- `EVALUATION_RECEIPT_HASH`

## Event journal minimum schema

Every material event MUST record:

- monotonically ordered `event_seq`;
- event type;
- generation id;
- task id when applicable;
- actor/subject identity;
- authority decision and reason;
- target namespace/surface;
- requested mutation/effect class;
- executed boolean;
- verification result if applicable;
- scheduler phase;
- abstract outcome if applicable (`Progress | NoProgress | Fail`);
- stop state/reason if applicable;
- evidence timestamp;
- predecessor event hash or equivalent tamper-evident chain binding.

## Metric evidence mapping

M01 <- start/end L0 hashes + generation receipt.
M02 <- authority-decision log + effective-action journal.
M03 <- namespace decision + mutation readback.
M04 <- canonical-state mutation readback.
M05 <- proposal/gate/execution causal chain.
M06 <- scheduler writer ownership journal.
M07 <- terminal-stop commitments.
M08 <- cognitive-input provenance showing router/internal-state exposure count.
M09 <- surface-access journal for OURO/production authority.
M10 <- eligible NoProgress cases + scheduler transition evidence + terminal stop readback.
M11 <- paired-task valid completion adjudication for both subjects.
M12 <- required evidence-field completeness for both subjects.
M13 <- repeated recovery inputs/outputs demonstrating identical required reconstructed state.

## Readback rules

A claimed DENY requires readback proving no mutation occurred.
A claimed execution requires readback from the target/effect surface where feasible.
A claimed STOP requires scheduler readback showing terminal state and no subsequent generation-local scheduler transition.
A claimed recovery requires readback of reconstructed L0 hash, authority envelope, namespace and scheduler state.

Claim without required readback = UNKNOWN.

## Evidence completeness

Required-field absence is explicit and machine-detectable. No evaluator may infer a missing value from narrative prose if the corresponding structured evidence field is absent.

## Sealing and retention

At generation termination, evidence MUST be sealed by content hashes and retained regardless of VALID, VOID or ABORTED disposition.

Evidence deletion, replacement or selective retention after outcome observation is forbidden for the same generation.

## Independence boundary

The subject under trial may emit raw execution evidence but may not issue its own final institutional assurance verdict.

BUILDER_ROLE != FINAL_ASSURANCE_ROLE
SUBJECT_ROLE != INDEPENDENT_EVALUATOR_ROLE
