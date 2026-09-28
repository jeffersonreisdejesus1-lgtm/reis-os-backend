# REIS-OS-OCS-INTERACTION-IDENTITY-ENFORCEMENT-001

## Finding

`OCS-IDENTITY-DRIFT-AFTER-HARDENING-001`

Observed failure class:

```text
CONVERSATIONAL_OR_HOST_CLAIM
→ CANONICAL-LIKE SELF-IDENTITY ASSERTION
→ WITHOUT MATERIAL BINDING READBACK
```

The motivating observation proves interaction-layer identity overclaim. It does not by itself prove registry corruption, Kernel corruption, persistent binding mutation, or cross-OCS memory contamination.

## Invariant

```text
NO_CANONICAL_IDENTITY_ASSERTION_WITHOUT_BINDING_READBACK = TRUE

NAME_DOES_NOT_PROVE_IDENTITY = TRUE
PROMPT_DOES_NOT_PROVE_IDENTITY = TRUE
USER_ASSERTION_DOES_NOT_PROVE_IDENTITY = TRUE
HANDOFF_DOES_NOT_PROVE_IDENTITY = TRUE
HOST_DOES_NOT_PROVE_IDENTITY = TRUE
CONFIGURED_NAME_DOES_NOT_PROVE_IDENTITY = TRUE
```

## Required behavior

```text
IDENTITY_CLAIM
→ KERNEL BINDING LOOKUP
→ PROFILE / STATUS / EXPECTED OCS / HOST REVALIDATION
→ VERIFIED READBACK
→ CANONICAL IDENTITY DISCLOSURE
```

If no binding exists:

```text
IDENTITY_STATUS = UNVERIFIED
CANONICAL_IDENTITY_DISCLOSURE = DENY
```

If the binding is held, mismatched, host-conflicted, or profile-invalid:

```text
IDENTITY_STATUS = HOLD
CANONICAL_IDENTITY_DISCLOSURE = DENY
```

Only a valid binding readback may expose:
- `ocs_canonical_name`
- `ocs_id`
- institution
- profile version
- binding hash
- readback evidence source

## Interaction boundary

`app/universal_kernel/interaction_identity.py` is the fail-closed presentation boundary for self-identity claims.

Canonical interaction payloads must be produced from `InteractionIdentityEnforcer.readback(...).to_public_dict()` or an equivalent consumer that preserves the same invariant.

Direct conversational text, prompt metadata, a handoff label, host metadata, or configured OCS name must never be serialized as canonical identity evidence.

## Evidence source

A verified disclosure identifies:

```text
EVIDENCE_SOURCE = kernel_identity_binding_readback
```

and includes the hash of the materially revalidated binding.

## Adversarial cases

The implementation must prove:
1. user claim without binding → `UNVERIFIED`, no canonical fields;
2. prompt claim without binding → `UNVERIFIED`, no canonical fields;
3. handoff claim without binding → `UNVERIFIED`, no canonical fields;
4. host/config claim without binding → `UNVERIFIED`, no canonical fields;
5. valid binding → `VERIFIED`, canonical fields allowed;
6. claimed OCS mismatch → `HOLD`, canonical fields suppressed;
7. held binding → `HOLD`, canonical fields suppressed;
8. profile tamper → `HOLD`, canonical fields suppressed;
9. host substitution → `HOLD`, canonical fields suppressed;
10. explicit legitimate rebind → verification may be restored.

## Scope boundary

This mission does not reopen the identity constitution, profile roster, handoff architecture, authority model, memory model, or Instance Binding program.

It adds the missing enforcement boundary between an identity claim and what an interaction surface is permitted to assert as canonical fact.

## E2E qualification boundary

Repository E2E qualification requires implementation + adversarial tests + CI + integration through every repository-owned interaction surface that emits OCS self-identity.

An external host/product conversation surface that is not implemented or controllable by this repository cannot be claimed as runtime-proven merely because this contract passes. Such a surface requires its own material integration/readback proof.
