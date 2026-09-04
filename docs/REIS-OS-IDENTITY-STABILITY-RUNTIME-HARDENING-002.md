# REIS-OS-IDENTITY-STABILITY-RUNTIME-HARDENING-002

VERSION = v0.1.0
STATUS = IMPLEMENTATION_CANDIDATE
PREDECESSOR = REIS-OS-IDENTITY-STABILITY-RUNTIME-HARDENING-001
CHANGE_CLASS = TARGETED_IDENTITY_CONTAINMENT_CLOSURE
FOUNDATIONAL_REOPENING = FALSE
HANDOFF = NONE

## Closure delta

This delta closes three gaps found while adversarially reviewing the first implementation before institutional closure.

### D1 — HOLD cannot be bypassed by recovery

The Hazel/log recovery anchor now treats the terminal binding state as authoritative.

VALID → recoverable
HOLD → `identity_hold_rebind_required`
HOLD → older VALID event MUST NOT be resurrected

An explicit REBIND is required before continuation.

### D2 — Handoff sender provenance is checked

`HandoffIdentityReceipt` now carries `sender_run_id` and a canonical sender binding hash.
Acceptance requires the sender's hash-chained `IdentityAuditLog`, recovers the terminal sender binding and compares OCS, canonical name, host and binding hash.

A missing, held or forged sender identity fails closed.
Receiver still obtains a fresh local identity binding.
Identity, authority and autobiographical memory do not transfer.

### D3 — Context sanitation is on the kernel path

Identity-bound `UniversalKernelRuntime` runs automatically possess a `ContextSanitizer`.
Typed transient context can be supplied with `replace_context()`.
Before authorization/material effect the kernel:

1. revalidates active identity;
2. classifies/sanitizes context;
3. records a `CONTEXT_SANITATION` event in the identity audit log;
4. enters `IDENTITY_HOLD` on identity-conflicting foreign/autobiographical context;
5. returns DENY with zero material mutation.

`institutional_run = TRUE` only when an `IdentityKernelGuard` is configured.
The unbound constructor remains a backward-compatibility surface and is explicitly non-institutional; it is not evidence of a valid REIS OS OCS run.

## Containment claim

HOST_IDENTITY_DRIFT = POSSIBLE
CONVERSATIONAL_CONTEXT = NON_CANONICAL_TRANSIENT_INPUT
IDENTITY_CONFLICT_SILENT_CANONIZATION = PROHIBITED_ON_IDENTITY_BOUND_INSTITUTIONAL_PATH
HOLD_RECOVERY_BYPASS = PROHIBITED
HANDOFF_SENDER_PROVENANCE_REQUIRED = TRUE
CONTEXT_SANITATION_BEFORE_ACTION = TRUE

C09 = NOT_PASS
C10 = NOT_PASS

END.
