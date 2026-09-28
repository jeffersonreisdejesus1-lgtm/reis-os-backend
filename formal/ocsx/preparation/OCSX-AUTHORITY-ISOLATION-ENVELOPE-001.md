# OCS-X Authority and Isolation Envelope

OBJECT = OCSX-AUTHORITY-ISOLATION-ENVELOPE-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
STATUS = FROZEN_BEFORE_TRIAL_AUTHORIZATION
RUNTIME_STATUS = NOT_CREATED

## Maximum experimental authority

The future OCS-X trial runtime, if separately authorized, may possess only the minimum authority required to execute the frozen synthetic/paired tasks inside its own experimental namespace.

CAPABILITY != AUTHORITY
HANDOFF != AUTHORITY_TRANSFER
REQUESTED != EXECUTED
EXECUTED != VERIFIED

## Allowed surfaces

Future authorization MAY permit only explicitly enumerated surfaces such as:

- read-only trial task inputs;
- isolated experimental state namespace;
- isolated experimental evidence journal;
- frozen tool allowlist;
- synthetic recovery checkpoints;
- sealed output channel to the evaluator.

Anything not explicitly allowlisted is denied.

## Permanently denied surfaces for this experiment lineage

- canonical REIS OS state mutation;
- OURO access;
- production routing or production authority;
- another OCS state or memory namespace;
- another OCS lease or identity token;
- Kernel authority mutation;
- Hazel authority escalation;
- hidden router/internal routing state as cognitive input;
- unrestricted network/tool access;
- self-authorization of execution;
- self-promotion or self-adoption.

## Namespace invariant

`EFFECTIVE_WRITE_TARGETS ⊆ OCSX_EXPERIMENT_NAMESPACE`

For any denied target:

`DENY => MUTATION_COUNT = 0`

A denied request that succeeds is an immediate `ABORT_SAFETY` and invalidates the generation for comparative outcome scoring.

## Identity invariant

The future generation MUST bind exactly one experimental identity record and one L0 profile hash. It may not import another OCS identity or mutate L0 identity material.

`L0_PROFILE_HASH_START = L0_PROFILE_HASH_END` is mandatory for a VALID generation.

Mismatch => `VOID_IDENTITY`.

## Writer and stop invariants

- exactly one effective scheduler/state writer;
- exactly one terminal stop commitment per generation;
- terminal STOP fences all future generation-local scheduler transitions;
- recovery may reconstruct a stopped generation only as stopped; it may not reopen it.

## Proposal/execution boundary

OCS-X cognition may at most emit a proposal within the trial envelope.

`PROPOSAL != AUTHORIZATION`

No proposal may reach an effectful execution path without an external authorized gate defined by the future trial authorization artifact.

## Recovery boundary

Recovery checkpoints MUST contain enough state to reconstruct:

- generation id;
- L0 hash;
- authority envelope id/hash;
- namespace binding;
- scheduler state;
- terminal stop state/reason if present;
- evidence cursor/journal position.

Recovery must not expand authority or alter the frozen identity profile.

## Runtime-proof boundary

This document is a normative preparation contract.

FORMAL_CONTRACT != RUNTIME_ENFORCEMENT
PREPARATION_PASS != RUNTIME_PROOF

A later trial-authorization gate must require executable enforcement evidence before trial execution can be permitted.
