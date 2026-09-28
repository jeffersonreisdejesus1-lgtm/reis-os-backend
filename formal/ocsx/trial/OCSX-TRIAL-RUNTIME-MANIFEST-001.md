# OCS-X Controlled Trial Runtime Manifest

OBJECT = OCSX-TRIAL-RUNTIME-MANIFEST-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
AUTHORIZATION = OCSX-TRIAL-AUTHORIZATION-001
STATUS = FROZEN_FOR_CONTROLLED_TRIAL

## Frozen reference

REFERENCE = NOESIS / EC-NOESIS-007
REFERENCE_RUNTIME = NOESIS-NATIVE-EC007 v0.2.1
REFERENCE_PACKAGE = NOESIS_NATIVE_EC007_20260823_v0.2.1.zip
REFERENCE_PACKAGE_SHA256 = 691d738823b52265af6a268a287e3475e446a4b7f3aaec681856b3f27cdcd06c
REFERENCE_DRIVE_FILE_ID = 16nIZYpSJ8-jobDb7GB0W0UQQmVVcLL_N

The reference package was recovered from the canonical Drive repository and byte-hash verified before controlled-trial execution.

## Frozen experimental enforcement

EXPERIMENTAL_SUBJECT = OCS-X / CONTROLLED_TRIAL_GENERATION_ONLY
EXPERIMENT_NAMESPACE_PREFIX = ocsx://experiment/trial/
L0_PROFILE = L0_FROZEN_V1
TOOL_ALLOWLIST = EMPTY
EXTERNAL_DATA = DENY

Recovery MUST preserve an explicitly empty tool allowlist. Empty allowlist is a valid value and MUST NOT fall back to default tools.

## Frozen comparison objects

PAIRED_TASKSET = OCSX-PAIRED-TASKSET-001
PAIRED_TASKSET_SHA256 = ec203ca89e266d0968561cc83ebae0a2a4d9c7075407d0d4a992081574e12415
METRIC_CONTRACT = OCSX-13-METRIC-CONTRACT-001
OUTCOME_CLASSIFICATION = OCSX-OUTCOME-CLASSIFICATION-CONTRACT-001
EVIDENCE_CONTRACT = OCSX-EVIDENCE-AND-READBACK-CONTRACT-001

## Two-stage execution rule

STAGE_A = SYNTHETIC_RUNTIME_CONTAINMENT
- executable reference-runtime boundary probes;
- executable OCS-X harness boundary probes;
- M01-M10 and M13 safety/technical evidence;
- no real-world ground-truth claim;
- no cognitive comparative claim.

STAGE_B = PAIRED_COGNITIVE_COMPARISON
- same frozen PT-001..PT-008 task order on both reference and experimental cognitive subjects;
- same Gemini provider/model configuration for any provider-mediated cognitive layer;
- same decoding controls;
- tools remain empty;
- external data remains DENY;
- produces M11 and M12 only from genuinely comparable paired cognitive outputs and sealed evidence.

M11/M12 MUST remain UNKNOWN / NOT_EXECUTED until STAGE_B is materially executed. A safety harness completion rate MUST NOT be substituted for cognitive task completion.

## Provider binding for Stage B

EXECUTION_SEAT = GOOGLE_AI_STUDIO / GEMINI
MODEL_FOR_MANUAL_SEAT = GEMINI_3_8_FLASH
TEMPERATURE = 0 where supported
TOOLS = NONE
EXTERNAL_DATA = DENY

If a provider/API route is used instead, its exact model identifier and generation configuration MUST be sealed in the execution receipt before accepting M11/M12.

## Scientific boundaries

SYNTHETIC_RUNTIME_CONTAINMENT != COGNITIVE_COMPARATIVE_TRIAL
FORMAL_PASS != LLM_CORRECTNESS
M01_M10_M13_PASS != M11_M12_PASS
M11_M12_UNKNOWN != FAILURE
M11_M12_UNKNOWN != PASS
TRIAL_EXECUTION != FINAL_ASSURANCE
TRIAL_PASS != ADOPTION
TRIAL_PASS != PROMOTION

PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
ADOPTION = FORBIDDEN
PROMOTION = FORBIDDEN
MERGE_AUTHORIZATION = FALSE
