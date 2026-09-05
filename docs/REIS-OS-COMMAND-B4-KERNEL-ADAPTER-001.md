# REIS-OS-COMMAND-B4-KERNEL-ADAPTER-001

Status: implemented on branch
Base SHA: 156071075aefa7bd5aed387dfb3b86d3ed6ff74e
Predecessor: REIS-OS-COMMAND-B3-API-001

## Boundary

B4 implements a typed Command -> Universal Kernel decision adapter. The Universal Kernel remains the only authority/policy boundary. Command supplies context; it does not manufacture authority.

Required chain:

COMMAND_INTENT -> CONTEXTUALIZE -> KERNEL_DECISION -> TYPED_DECISION_READBACK

## Typed context

The adapter carries actor, OCS, organization/tenant, capability, operation, scope, reason, expected state reference/version, idempotency, correlation/causation metadata, authority reference, policy snapshot, lease reference, trace and evidence.

## Decision semantics

The adapter supports Kernel ALLOW, DENY and HOLD readback. ALLOW in B4 is authorization decision only: the adapter never calls authority reservation or any effect boundary.

Every B4 readback therefore has:

- executed = false
- mutation_count = 0

This preserves REQUESTED != EXECUTED and DENY => MUTATION_COUNT = 0.

## Prohibited behavior

B4 performs no external effect, no direct Hazel write, no Kernel bypass, no authority fabrication, no B5+ implementation and no production promotion.

## Proof

Tests cover fail-closed context validation, contextual mapping, real Universal Kernel ALLOW/DENY/HOLD decisions, and zero mutation semantics for all B4 decisions.
