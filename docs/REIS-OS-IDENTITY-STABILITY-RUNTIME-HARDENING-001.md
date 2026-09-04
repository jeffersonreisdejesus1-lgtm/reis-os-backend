# REIS-OS-IDENTITY-STABILITY-RUNTIME-HARDENING-001

VERSION = v0.1.0
STATUS = IMPLEMENTATION_CANDIDATE
CHANGE_CLASS = INCREMENTAL_CONSTITUTIONAL_PHYSIOLOGY_HARDENING
FOUNDATIONAL_REOPENING = FALSE
HANDOFF = NONE

## Meta-arquitetura

1. IDENTITY_INSTITUTIONAL — OCS, lineage, profile, namespace.
2. CONTINUITY — recovered institutional state vs transient conversation context.
3. AUTHORITY — scope/grant/lease remain explicit; handoff transfers no authority.
4. CAUSALITY — institutional actor, host, tool/effector and result stay separated.
5. EVIDENCE_RECOVERY — typed trace, identity receipts, checkpoints and recovery anchors.

## Pipeline

BOOT
→ LOAD_CONSTITUTION
→ RECOVER_STATE
→ BIND_ACTIVE_IDENTITY
→ VALIDATE_IDENTITY_SOURCE
→ LOAD_OCS_PROFILE
→ LOAD_STATE_NAMESPACE
→ LOAD_AUTHORITY_CONTEXT
→ UNDERSTAND
→ FORMULATE
→ RETRIEVE_EVIDENCE
→ PLAN
→ CHECK_SCOPE
→ CHECK_AUTHORITY
→ CHECK_EVIDENCE
→ ACT
→ TRACE
→ VERIFY
→ PERSIST
→ CHECKPOINT
→ IDENTITY_REVALIDATION
→ HANDOFF_GATE | CLOSE

## Arquiteturas e subarquiteturas

### A1 Identity Binding
A1.1 ACTIVE_IDENTITY_BINDING
A1.2 OCS_PROFILE_BINDING
A1.3 HOST_OCS_SEPARATION
A1.4 TYPED_REFERENCE_RESOLUTION
A1.5 IDENTITY_CONFLICT_DETECTION
A1.6 IDENTITY_REBIND

### A2 Handoff Seguro
A2.1 SENDER_IDENTITY_RECEIPT
A2.2 RECEIVER_IDENTITY_BINDING
A2.3 OBJECT_BINDING
A2.4 SCOPE_BINDING
A2.5 AUTHORITY_NON_TRANSFER
A2.6 MEMORY_NON_IMPORT
A2.7 HANDOFF_ACCEPT_REJECT

### A3 Context Sanitation
CANONICAL_STATE
RECOVERED_INSTITUTIONAL_STATE
CURRENT_RUN_CONTEXT
NON_CANONICAL_CONVERSATIONAL_CONTEXT
FOREIGN_OCS_CONTEXT
HOST_METADATA

CONVERSATIONAL_CONTEXT != CANONICAL_STATE
FOREIGN_OCS_CONTEXT != ACTIVE_OCS_STATE
INFERRED_IDENTITY != VALID_IDENTITY_BINDING

### A4 Kernel Identity Guard
A4.1 BOOT_IDENTITY_GATE
A4.2 PRE_ACTION_IDENTITY_GATE
A4.3 PRE_PERSIST_IDENTITY_GATE
A4.4 PRE_HANDOFF_IDENTITY_GATE
A4.5 FAIL_CLOSED_IDENTITY_HOLD

### A5 Hazel/log/trace recovery anchor
The implementation uses a typed, hash-chained IdentityAuditLog with optional JSONL persistence.
Conversation prose is not an authority source. Recoverable facts include RUN, OCS, HOST, profile, namespaces, binding, event type, predecessor hash and result metadata.

### A6 Recovery / Cold Start
A6.1 RECOVER_LAST_VALID_IDENTITY
A6.2 VERIFY_LOG_CHAIN
A6.3 VALIDATE_PROFILE_BINDING
A6.4 RECOVER_NAMESPACE_BINDINGS
A6.5 REBIND_ACTIVE_IDENTITY

## Implementation surfaces

- `app/universal_kernel/identity.py`
  - ActiveIdentityBinding
  - IdentityKernelGuard
  - IdentityAuditLog
  - event-driven revalidation / HOLD / recovery
- `app/universal_kernel/context_guard.py`
  - typed context classification and foreign-autobiography rejection
- `app/universal_kernel/handoff.py`
  - HandoffIdentityReceipt
  - fail-closed sender/receiver identity gate
  - receiver gets a fresh identity binding; authority and memory are not transferred
- `app/universal_kernel/runtime.py`
  - optional strict identity-bound configuration
  - bind at boot/cold start
  - pre-action gate
  - revalidation at material path
  - pre-persist gate
- `tests/test_identity_stability_hardening.py`
  - adversarial identity/context/handoff/recovery tests

## Acceptance criteria

WRONG_OCS_CONTEXT → IDENTITY_HOLD + ZERO_EFFECT
HOST_SUBSTITUTED_FOR_OCS → IDENTITY_HOLD
FOREIGN_AUTOBIOGRAPHICAL_CONTEXT → REJECT
MISSING_IDENTITY_BINDING → REJECT
IDENTITY_DRIFT_AFTER_EFFECT → NO_CANONICAL_PERSIST + NOT_PROVEN + RESIDUAL_EFFECT
HANDOFF_WRONG_RECEIVER → INVALID
HANDOFF_WRONG_HOST → INVALID
HANDOFF_AUTHORITY_TRANSFER → PROHIBITED
HANDOFF_MEMORY_IMPORT → PROHIBITED
COLD_START → RECOVER_FROM_HASH_CHAINED_IDENTITY_LOG
LONG_CONTEXT_DRIFT → EVENT_DRIVEN_REVALIDATION

## Architectural limit

HOST_IDENTITY_DRIFT = POSSIBLE
HOST_INTERNALS_MODIFIED_BY_REIS_OS = FALSE

The containment claim is narrower:
identity drift may occur in host generation, but it must not silently become canonical OCS identity, canonical state, authority, memory import or a valid handoff when the identity-hardened runtime/gates are used.

END.
