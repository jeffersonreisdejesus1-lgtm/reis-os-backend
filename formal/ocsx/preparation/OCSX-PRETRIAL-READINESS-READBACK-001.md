# OCS-X Pretrial Readiness Readback

OBJECT = OCSX-PRETRIAL-READINESS-READBACK-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
BUILDER = DEDALA
SELF_ASSURANCE = PROHIBITED

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

## CI infrastructure reservation

The dedicated workflow repeatedly creates the `pretrial-enforcement` job and terminates before exposing any step.

Observed dedicated exact-head run:
- RUN_ID = 34171193372
- HEAD = 5a226b098ff3f95ff28030eafcacb5f92318b7cf
- EVENT = push
- CONCLUSION = failure

Predecessor run 34170966340 was explicitly rerun once. Both the original attempt and rerun completed `failure` with `steps=[]`. Job-log retrieval for the rerun returned GitHub storage `BlobNotFound`; therefore no executable test failure is evidenced.

CI_INFRASTRUCTURE_RESERVATION = PRE_STEP_FAILURE_NO_LOG_BLOB
CODE_TEST_FAILURE = NOT_PROVEN
CI_PASS = NOT_CLAIMED
RETRY_LOOP = PROHIBITED_WITHOUT_NEW_SIGNAL

## Builder disposition

PRETRIAL_IMPLEMENTATION = MATERIALIZED
PRETRIAL_EVIDENCE_MODEL = MATERIALIZED
PRETRIAL_TASKSET = FROZEN
OUTCOME_CLASSIFICATION = FROZEN
REPRODUCIBILITY_CONTRACT = FROZEN
CI_INFRASTRUCTURE_RESERVATION = OPEN

DÉDALA_DISPOSITION = READY_FOR_INDEPENDENT_PRETRIAL_ASSURANCE_WITH_CI_RESERVATION

This disposition is not `PRETRIAL_PREPARATION = COMPLETE`. Only an independent competent reviewer may decide whether the external CI infrastructure reservation blocks or qualifies the G0 exit.

MAX_BUILDER_CONSEQUENCE = HANDOFF_FOR_ASSURANCE
TRIAL_AUTHORIZATION_REQUEST = NOT_READY

OCS_X_CREATION = FORBIDDEN
L1_ACTIVATION = FORBIDDEN
TRIAL_EXECUTION = FORBIDDEN
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN
MERGE = NOT_AUTHORIZED
