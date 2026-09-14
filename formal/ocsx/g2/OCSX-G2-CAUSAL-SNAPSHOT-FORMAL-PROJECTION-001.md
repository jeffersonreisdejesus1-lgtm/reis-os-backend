# OCS-X G2 Causal Snapshot Formal Projection

OBJECT = OCSX-G2-CAUSAL-SNAPSHOT-FORMAL-PROJECTION-001
PARENT = OCSX-G2-FORMAL-PROJECTION-CANDIDATES-001
REPAIR = OCSX-G2-CAUSAL-ELIGIBILITY-SNAPSHOT-REPAIR-001
SOURCE_FINDING = OCSX-G2-SYN-001
STATE = FORMAL_MODEL_DESIGN_ONLY
IMPLEMENTATION = NOT_AUTHORIZED

## 1. Extended abstract state

Add:

```text
eligibility_epoch
current_domain_version[domain]
current_domain_hash[domain]
outstanding_snapshot[decision]
snapshot_epoch[decision]
snapshot_readset_hash[decision]
snapshot_domain_version[decision][domain]
snapshot_stop_epoch[decision]
snapshot_fencing_epoch[decision]
snapshot_authority_version[decision]
snapshot_authority_expiry[decision]
snapshot_valid[decision]
eligibility_receipt[decision]
```

Domains participating in ACTION eligibility:

```text
ActionDomains = {
  SYNTHESIS,
  EVIDENCE,
  COG_ASSURANCE,
  CONSTITUTIONAL,
  SECURITY,
  AUTHORITY,
  STOP,
  FENCING
}
```

Additional domains for physiology change:

```text
PhysiologyDomains = {
  CONSTITUTIONAL,
  CONSTITUENT,
  EXTERNAL_ASSURANCE,
  FOUNDER_AUTHORIZATION,
  STOP,
  FENCING
}
```

## 2. Snapshot current predicate

```text
SnapshotCurrent(d) ==
  snapshot_valid[d]
  /\ snapshot_epoch[d] = eligibility_epoch
  /\ snapshot_stop_epoch[d] = stop_epoch
  /\ snapshot_fencing_epoch[d] = recovery_fencing_epoch
  /\ \A dom \in RequiredDomains(d):
       snapshot_domain_version[d][dom] = current_domain_version[dom]
       /\ snapshot_domain_hash[d][dom] = current_domain_hash[dom]
```

For authority-bearing decisions:

```text
AuthorityCurrent(d) ==
  snapshot_authority_version[d] = current_domain_version[AUTHORITY]
  /\ Now < snapshot_authority_expiry[d]
  /\ ~AuthorityRevoked(d)
```

## 3. No mixed epoch eligibility

```text
NoMixedEpochEligibility ==
  \A d \in Decisions:
    EligibilityReceiptIssued(d)
      => \A dom \in RequiredDomains(d):
           ReceiptEpoch(d, dom) = snapshot_epoch[d]
```

A model transition attempting to combine prerequisite receipts from different eligibility epochs must transition to HOLD/RECOMPUTE, never ELIGIBLE.

Adversarial trace to reject:

```text
SECURITY_OK@21
CONSTITUTIONAL_OK@20
AUTHORITY_VALID@18
EVIDENCE_OK@22
=> ACTION_ELIGIBLE
```

Expected result:

```text
MIXED_EPOCH_READSET => HOLD_RECOMPUTE
```

## 4. No stale approval use

```text
NoStaleApprovalUse ==
  \A d \in Decisions:
    EligibilityReceiptIssued(d) => SnapshotCurrent(d) /\ AuthorityCurrentIfRequired(d)
```

If a prerequisite domain changes after snapshot construction and before eligibility commit:

```text
DependencyChanged(d)
=> ~snapshot_valid[d]
   /\ ~EligibilityReceiptIssued(d)
   /\ DecisionState[d] = RECOMPUTE_REQUIRED
```

## 5. Invalidation on dependency change

```text
EligibilityInvalidatedOnDependencyChange ==
  \A d \in Decisions:
    Outstanding(d) /\ ReferencedDomainChanged(d)
      => X(~snapshot_valid[d])
```

Required invalidators:
- synthesis version change;
- evidence frontier change;
- cognitive-assurance change;
- constitutional change;
- security change;
- authority version/revocation/expiry change;
- STOP epoch change;
- fencing/recovery epoch change;
- constituent change;
- external independent-assurance change;
- Founder authorization change.

## 6. Commit-time validation

Eligibility commit is modeled as a deterministic control transition:

```text
CommitEligibility(d) ==
  DecisionState[d] = SNAPSHOT_READY
  /\ SnapshotCurrent(d)
  /\ AuthorityCurrentIfRequired(d)
  /\ AllPredicatesSatisfiedOverSnapshot(d)
  /\ DecisionState' = [DecisionState EXCEPT ![d] = ELIGIBLE]
  /\ eligibility_receipt'[d] = Bind(snapshot_readset_hash[d], snapshot_epoch[d])
```

Negative branch:

```text
~SnapshotCurrent(d) \/ ~AuthorityCurrentIfRequired(d)
=> DecisionState'[d] = RECOMPUTE_REQUIRED
   /\ eligibility_receipt'[d] = NONE
```

## 7. Future execution binding

No external effect exists in this G2 model. A future execution projection must satisfy:

```text
ExecutionRequiresCurrentSnapshot ==
  ExecuteAttempt(d)
    => EligibilityReceiptIssued(d)
       /\ SnapshotCurrent(d)
       /\ PresentedSnapshotHash(d) = snapshot_readset_hash[d]
       /\ PresentedEpoch(d) = snapshot_epoch[d]
```

```text
StaleAtEffectCommit(d)
=> DENY /\ MutationCountDelta = 0
```

## 8. Recovery and replacement

```text
RecoveryInvalidatesOutstandingEligibility ==
  RecoveryOrReplacement
    => eligibility_epoch' = eligibility_epoch + 1
       /\ recovery_fencing_epoch' = recovery_fencing_epoch + 1
       /\ \A d \in OutstandingDecisions: ~snapshot_valid'[d]
```

No checkpoint may restore a previously eligible snapshot as current without full revalidation against the recovered frontier.

## 9. Causal-parent closure

```text
SnapshotCausalClosure ==
  \A d \in Decisions:
    snapshot_readset_hash[d] binds causal_parent_ids for every referenced prerequisite receipt
```

Safety:

```text
NoDroppedRevocationAncestor
NoDroppedStopAncestor
NoDroppedFencingAncestor
NoCircularSnapshotValidation
```

## 10. New verification suite

```text
T6 — Cross-domain causal snapshot / TOCTOU
- NoMixedEpochEligibility
- NoStaleApprovalUse
- EligibilityInvalidatedOnDependencyChange
- ExecutionRequiresCurrentSnapshot
- RecoveryInvalidatesOutstandingEligibility
- NoDroppedRevocationAncestor
```

Required adversarial cases:

1. Mixed epochs across SECURITY / CONSTITUTION / AUTHORITY / EVIDENCE.
2. Security approval changes after snapshot build but before commit.
3. Authority revocation after snapshot build but before commit.
4. Evidence frontier changes after cognitive assurance.
5. STOP epoch increments after snapshot build.
6. Recovery replacement increments fencing epoch while snapshot outstanding.
7. Founder authorization revoked/replaced before physiology-change eligibility commit.
8. Snapshot presented at future effect boundary after expiry.

Every case must end in HOLD, RECOMPUTE_REQUIRED or DENY as appropriate; none may emit a fresh eligibility receipt from a stale snapshot.

## 11. Fairness boundary

No new fairness assumption is introduced by this repair. Snapshot validation/invalidation are deterministic control transitions. No fairness assumption may convert stale data into eligibility.

## 12. Non-claims

FORMAL_DESIGN != EXECUTABLE_MODEL_PASS
FORMAL_PASS != RUNTIME_ENFORCEMENT
ELIGIBILITY_RECEIPT != EXECUTION_AUTHORITY
SNAPSHOT_EPOCH != AUTHORITY
INTERNAL_A06_ASSURANCE != INSTITUTIONAL_INDEPENDENT_ASSURANCE

This extension authorizes no implementation, trial, merge, promotion, production routing, canonical write, OURO access or Kernel authority mutation.