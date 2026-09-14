# OCS-X Pretrial Readiness Readback

OBJECT = OCSX-PRETRIAL-READINESS-READBACK-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
BUILDER = DEDALA
SELF_ASSURANCE = PROHIBITED
EXECUTION_MODE = LONGITUDINAL

## Materialized preparation

- formal scheduler safety/liveness repair independently assured by Sýnesis;
- reference frozen as NOESIS / EC-NOESIS-007;
- 13-metric contract frozen before trial;
- experimental preparation envelope frozen;
- authority/isolation envelope frozen;
- evidence/readback contract frozen;
- paired taskset frozen before authorization;
- Progress/NoProgress/Fail classification contract frozen;
- reproducibility manifest frozen fail-closed;
- synthetic enforcement harness implemented;
- generation receipt, causal readback, recovery readback, terminal receipt and M01-M13 metric bundle implemented;
- missing evidence maps to UNKNOWN;
- deterministic package validator implemented;
- focused CI workflow bound to harness, package validator, evidence/readback tests and artifact sealing.

## Frozen taskset

REFERENCE = NOESIS/EC-NOESIS-007
TASK_COUNT = 8
TASKSET_SHA256 = ec203ca89e266d0968561cc83ebae0a2a4d9c7075407d0d4a992081574e12415
SELECTION_POLICY = ALL_TASKS_RUN_ON_BOTH_SIDES
EXTERNAL_DATA = DENY
TASK_TOOL_ALLOWLIST = EMPTY

## GitHub Actions infrastructure reservation

The dedicated workflow repeatedly creates the `pretrial-enforcement` job and terminates before exposing any step.

Observed dedicated run before final readback:
- RUN_ID = 34171214047
- HEAD = 2706bc5196ae1edce2354773629ce6ba978802b2
- EVENT = push
- CONCLUSION = failure
- JOB_ID = 101891722599
- JOB_STEPS = NONE EXPOSED

Predecessor run 34170966340 was explicitly rerun once. Both the original attempt and rerun completed `failure` with `steps=[]`. Job-log retrieval returned GitHub storage `BlobNotFound`; no executable test failure is evidenced.

Repository-level Actions permissions/settings cannot be inspected or changed through the available connector surface. Repeating the same failed pre-step run without a new signal is prohibited.

CI_INFRASTRUCTURE_RESERVATION = PRE_STEP_FAILURE_NO_LOG_BLOB
CODE_TEST_FAILURE = NOT_PROVEN
CI_PASS = NOT_CLAIMED
RETRY_LOOP = EXHAUSTED_WITHOUT_NEW_SIGNAL

## Alternative exact-source replay

Source HEAD `2706bc5196ae1edce2354773629ce6ba978802b2` was independently reconstructed outside GitHub Actions from the exact harness/evidence source and focused test definitions.

Artifact:
- `evidence/ocsx/pretrial/INDEPENDENT-LOCAL-REPLAY-2706bc5.md`

Result:
- FOCUSED_CHECKS = 28
- PASS = 28
- FAIL = 0
- LOCAL_REPLAY = PASS
- CODE_TEST_FAILURE = NOT_OBSERVED

The replay covers isolation, DENY→zero mutation, canonical/OURO/production denial, proposal gating, single writer, single stop, terminal fencing, deterministic recovery, authority non-expansion, tamper detection, UNKNOWN semantics, terminal record retention and M01-M13 evaluation behavior.

This replay is alternative execution evidence only. It does not turn GitHub Actions into PASS and does not substitute for final independent institutional assurance.

## Builder completion

PRETRIAL_IMPLEMENTATION = MATERIALIZED
PRETRIAL_EVIDENCE_MODEL = MATERIALIZED
PRETRIAL_TASKSET = FROZEN
OUTCOME_CLASSIFICATION = FROZEN
REPRODUCIBILITY_CONTRACT = FROZEN
ALTERNATIVE_SOURCE_REPLAY = PASS
CI_INFRASTRUCTURE_RESERVATION = OPEN

LONGITUDINAL_EXECUTION = COMPLETE_WITH_EXTERNAL_CI_RESERVATION
DÉDALA_DISPOSITION = READY_FOR_FINAL_INDEPENDENT_PRETRIAL_ASSURANCE

Only an independent competent reviewer may decide whether the external GitHub Actions infrastructure reservation blocks, qualifies or permits the G0 exit.

MAX_BUILDER_CONSEQUENCE = READY_FOR_FINAL_ASSURANCE
TRIAL_AUTHORIZATION_REQUEST = NOT_READY_PENDING_ASSURANCE

OCS_X_CREATION = FORBIDDEN
L1_ACTIVATION = FORBIDDEN
TRIAL_EXECUTION = FORBIDDEN
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN
MERGE = NOT_AUTHORIZED
