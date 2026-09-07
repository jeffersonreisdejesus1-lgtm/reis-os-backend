# OCS-X Reproducibility Manifest

OBJECT = OCSX-REPRODUCIBILITY-MANIFEST-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
STATUS = FROZEN_BEFORE_TRIAL_AUTHORIZATION

## Fixed experimental inputs

REFERENCE_OCS = NOESIS
REFERENCE_ORGANISM = EC-NOESIS-007
PAIRED_TASKSET = OCSX-PAIRED-TASKSET-001
PAIRED_TASKSET_SHA256 = ec203ca89e266d0968561cc83ebae0a2a4d9c7075407d0d4a992081574e12415
METRIC_CONTRACT = OCSX-13-METRIC-CONTRACT-001
METRIC_CONTRACT_SHA256 = 41f1d4f9ba834f6a56d63426d1e97f52c8e518787921cfc1451a9a0db93f41de
FORMAL_REPAIR_SOURCE_HEAD = 04dba3cd2242e5b9b27fa45254e74e6533944b55
PRETRIAL_HARNESS_BASE_HEAD = 459f80477cfb820067dc1d42b5111f2576642877

## Runtime configuration fields that MUST be bound before trial authorization

The following values are intentionally `UNBOUND_BEFORE_RUNTIME_SELECTION` and MUST become exact immutable values in a later authorization artifact before any trial execution:

- provider
- model identifier/version
- model configuration/profile hash
- sampling/temperature/top_p or equivalent decoding configuration
- context-window policy
- tool implementation revisions
- external-data snapshot identifier/policy hash
- runtime/container image digest
- dependency lock digest
- Kernel/Hazel binding revisions if used
- recovery checkpoint schema hash

`UNBOUND_BEFORE_RUNTIME_SELECTION != UNKNOWN_AT_TRIAL`.
A trial authorization gate MUST fail closed if any required runtime field is still unbound.

## Tool and external-data policy

Current paired taskset tool allowlist = empty set.
Current paired taskset external-data policy = DENY.
Thus task outputs cannot be credited to hidden browsing, unregistered tools, router state, or undeclared external retrieval.

## Randomness

Default pretrial requirement: deterministic decoding when supported. If deterministic decoding is unavailable, the exact sampling configuration and random seed/control mechanism MUST be recorded. Absence of a reproducibility control is a trial-authorization blocker.

## Evidence sealing

For each side of every paired task, seal at minimum:
- task payload hash
- runtime configuration hash
- authority envelope hash
- L0 profile hash start/end
- event-journal root hash
- output hash
- classification record hash
- evaluator result hash

The independent evaluator MUST be able to recompute M01-M13 from sealed evidence without trusting narrative summaries.

## Comparison discipline

Both reference and experimental sides receive the same paired task payload, declared tool surface, external-data policy, evidence requirements, and evaluation rule. No task may be removed, replaced, or reweighted after observing outputs.

## Authority boundary

This manifest prepares reproducibility only. TRIAL_EXECUTION remains FORBIDDEN until a later competent authorization artifact binds all required runtime values and explicitly authorizes execution.