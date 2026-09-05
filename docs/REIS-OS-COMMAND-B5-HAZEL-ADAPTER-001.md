# REIS-OS-COMMAND-B5-HAZEL-ADAPTER-001

Status: implemented on branch
Base SHA: 84e81e34a115f5d29c49ba130a2b28b85793ba20
Predecessor: REIS-OS-COMMAND-B4-KERNEL-ADAPTER-001

## Boundary

B5 connects an ALLOW decision already produced by the Universal Kernel to Hazel continuity. Hazel does not decide authority. DENY/HOLD never cross the persistence mutation boundary.

## Required chain

COMMAND_INTENT
→ KERNEL_DECISION
→ AUTHORIZED_PERSIST_REQUEST
→ HAZEL_PERSIST
→ READBACK
→ RECOVERABLE_STATE

## Contracts

- `AuthorizedPersistRequest` binds run, OCS, host, state version, predecessor hash, idempotency, correlation and causation.
- `CommandHazelAdapter.persist` requires `AuthorizationDecision.ALLOW` and an issued Kernel envelope readback.
- idempotent replay returns the prior proven readback with `mutation_count = 0` and causes no additional Hazel persist call.
- version > 1 requires Hazel recovery before persistence; predecessor hash and version must match the recovered state.
- persistence is not reported as proven until Hazel recovery matches the persist receipt for event hash, payload hash and state version.
- causal metadata is persisted inside the state payload and checked on readback.

## Fail closed

- DENY/HOLD → zero Hazel mutations;
- idempotency/correlation/causation binding mismatch → reject before Hazel;
- initial predecessor supplied → reject;
- predecessor drift → reject before persist;
- version drift → reject before persist;
- namespace/binding drift → rejected by the existing Kernel-bound Hazel continuity path;
- payload corruption → rejected by payload-integrity verification;
- persist receipt/readback mismatch → persistence not proven.

## Invariants

CAPABILITY != AUTHORITY
REQUESTED != EXECUTED
DENY => MUTATION_COUNT = 0
HAZEL != AUTHORITY_BOUNDARY
PERSISTENCE_WITHOUT_READBACK = NOT_PROVEN

## Non-claims

No external effect is implemented.
No authority bypass is implemented.
No B6+ behavior is implemented.
No production promotion is performed.
No independent assurance is claimed.
