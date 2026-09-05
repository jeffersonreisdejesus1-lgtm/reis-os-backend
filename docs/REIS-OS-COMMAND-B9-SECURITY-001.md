# REIS-OS-COMMAND-B9-SECURITY-001

Status: implemented on branch
Base SHA: 3e89918d796dfe9feb90792dea9ad6e5973b9ad5

B9 hardens Command boundaries without creating a new authority boundary.

## Existing API boundary hardened

- authentication remains mandatory through `CurrentUser`;
- exact institutional organization binding remains mandatory;
- ordinary Command reads require active OWNER or ADMIN membership;
- founder-sensitive surface `/v1/command/security/posture` requires active OWNER membership.

## Request guard

`CommandSecurityGuard` provides fail-closed validation for pre-effect Command requests:
- organization binding;
- role enforcement;
- founder-sensitive owner enforcement;
- OCS namespace isolation against canonical profile state/memory namespaces;
- required request fields;
- idempotent replay recognition;
- conflicting replay rejection;
- secret/token/password/API-key redaction in structured audit readback;
- deny paths always report `mutation_count = 0`.

The guard does not execute requests and does not create or expand authority.

## Device/session support

No additional device/session binding is materially present in this backend slice. The security posture therefore reports `device_session_binding = not_materialized`; B9 does not fabricate support.

## Auditability

B9 returns structured security audit metadata with sensitive values redacted and idempotency keys hashed. This is not claimed to be a durable institutional audit log.

## Non-negotiable invariants

CAPABILITY != AUTHORITY
REQUESTED != EXECUTED
EXECUTED != VERIFIED
VERIFIED != ASSURED
DENY => MUTATION_COUNT = 0
CROSS_OCS_WRITE = FORBIDDEN
AUTHORITY_BYPASS = FORBIDDEN
UNSUPPORTED_CLAIM = FORBIDDEN

B10 is not started by this branch.
