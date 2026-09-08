# Handoff — OCS-X G2 Dédala to Sýnesis Re-entry

HANDOFF_ID = HANDOFF-OCSX-G2-DEDALA-TO-SYNESIS-REENTRY-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
SOURCE = DÉDALA
TARGET = SÝNESIS
OBJECT = OCSX-G2-SYN-001
AUTHORITY_TRANSFERRED = FALSE

## Repair closure scope

The HIGH finding `CROSS_DOMAIN_CAUSAL_CONSISTENCY / TOCTOU` was accepted without contestation.

Repair artifacts:

- `formal/ocsx/g2/OCSX-G2-CAUSAL-ELIGIBILITY-SNAPSHOT-REPAIR-001.md`
- `formal/ocsx/g2/OCSX-G2-CAUSAL-SNAPSHOT-FORMAL-PROJECTION-001.md`

The repair introduces:

- mission-local monotonic `EligibilityEpoch`;
- immutable `DecisionSnapshot / EligibilityReadSet`;
- version/hash binding for all prerequisite domains;
- authority lease version, expiry and revocation binding;
- STOP and recovery/fencing epoch binding;
- evidence/provenance frontier binding;
- two-phase snapshot build then commit-time currentness validation;
- deterministic stale => HOLD/RECOMPUTE semantics;
- future execution request binding to exact snapshot/readset hash/epoch;
- invalidation on any dependency change;
- recovery/replacement invalidation of outstanding snapshots;
- immutable causal-parent closure;
- formal properties `NoMixedEpochEligibility`, `NoStaleApprovalUse`, `EligibilityInvalidatedOnDependencyChange`, `ExecutionRequiresCurrentSnapshot`, and `RecoveryInvalidatesOutstandingEligibility`;
- adversarial TOCTOU cases for mixed epochs, authority revocation, STOP, fencing/recovery, evidence changes and Founder authorization changes.

The non-blocking A06 reservation is also architecturally specified: separate instance/context, no authorship or mutation of target cognition, immutable-reference review, private-working-memory separation, provider/model diversity recommended but not sufficient for institutional independence, and external independent assurance still mandatory for physiology change.

## Requested Sýnesis action

Perform independent architecture re-entry on the exact PR #74 head containing this handoff and verify that:

1. mixed-epoch prerequisite composition cannot yield eligibility;
2. stale approvals cannot be consumed after a dependency mutation;
3. any prerequisite-domain change invalidates outstanding eligibility;
4. future effect execution is constrained to exact current snapshot binding;
5. recovery/replacement invalidates or revalidates outstanding snapshots;
6. causal-parent closure preserves revocation/STOP/fencing ancestry;
7. A06 independence boundaries do not create internal sovereign assurance;
8. no implementation, Founder implementation gate, merge, promotion, production, canonical write or OURO authority was inferred from this repair.

## Boundary

OCS_X_G2_IMPLEMENTATION = NOT_AUTHORIZED
FOUNDER_IMPLEMENTATION_GATE = NOT_CLEARED
MERGE = NOT_AUTHORIZED
PROMOTION = NOT_AUTHORIZED
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
OURO_ACCESS = FORBIDDEN

HANDOFF != AUTHORITY_TRANSFER
BUILDER_ROLE != FINAL_ASSURANCE_ROLE
