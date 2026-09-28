# OCS-X G2 Causal Eligibility Snapshot Repair

OBJECT = OCSX-G2-CAUSAL-ELIGIBILITY-SNAPSHOT-REPAIR-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
SOURCE_FINDING = OCSX-G2-SYN-001
SOURCE_ASSURANCE_HEAD = 704fee478ada7a80bc97fe4248a81d7888e00e2c
ARCHITECT = DÉDALA
STATE = ARCHITECTURE_REPAIR_CANDIDATE
IMPLEMENTATION = NOT_AUTHORIZED

## 1. Scope

This artifact repairs only the cross-domain causal-consistency / TOCTOU gap found by Sýnesis in G2. It is additive to:

- `OCSX-G2-MULTIAGENT-CONSTITUTIONAL-ARCHITECTURE-001`
- `OCSX-G2-FORMAL-PROJECTION-CANDIDATES-001`

It does not authorize implementation, trial, production routing, canonical writes, OURO access, adoption, promotion, universal rollout or merge.

## 2. New primitive: EligibilityEpoch

G2 introduces a monotonically increasing mission-local causal epoch:

```text
EligibilityEpoch:
    mission_id: string
    generation: string
    epoch: uint64
    global_stop_epoch: uint64
    recovery_fencing_epoch: uint64
    created_at: timestamp
```

The epoch is not authority. It is only a causal-consistency coordinate.

Any material change in a prerequisite state domain MUST advance the eligibility epoch before a new decision may become eligible.

Dependency changes that invalidate prior eligibility include at minimum:

- synthesis state or cognitive-acceptance inputs;
- evidence/provenance frontier;
- cognitive-assurance finding;
- constitutional finding;
- security finding;
- authority lease/version/expiry/revocation;
- STOP state or stop epoch;
- fencing/recovery epoch;
- constituent finding;
- Founder authorization state for physiology change.

## 3. DecisionSnapshot / EligibilityReadSet

Every candidate action or physiology-change decision MUST carry an immutable read set:

```text
DecisionSnapshot:
    snapshot_id: string
    mission_id: string
    generation: string
    decision_id: string
    decision_type: enum{ACTION, PHYSIOLOGY_CHANGE}
    eligibility_epoch: uint64
    causal_parent_ids: ordered_set<MessageOrReceiptId>

    synthesis_version: VersionHash | NOT_APPLICABLE
    evidence_frontier_hash: sha256
    cognitive_assurance_version: VersionHash | NOT_APPLICABLE
    constitutional_version: VersionHash
    security_version: VersionHash | NOT_APPLICABLE
    authority_lease_ref: string | NOT_APPLICABLE
    authority_lease_version: VersionHash | NOT_APPLICABLE
    authority_lease_expires_at: timestamp | NOT_APPLICABLE
    stop_epoch: uint64
    fencing_epoch: uint64
    constituent_version: VersionHash | NOT_APPLICABLE
    founder_authorization_version: VersionHash | NOT_APPLICABLE

    readset_hash: sha256
    created_at: timestamp
```

`readset_hash` binds every field above in canonical serialization.

No prerequisite may be represented only as an unversioned boolean such as `SECURITY_OK=true`. Every positive prerequisite consumed by eligibility MUST resolve to a version/hash in the same `DecisionSnapshot`.

## 4. Snapshot construction

Only A02 COORDINATION may assemble a candidate snapshot, but assembly does not grant eligibility and does not mutate owned prerequisite domains.

Each prerequisite owner returns an immutable versioned receipt bound to:

```text
mission_id
generation
decision_id
eligibility_epoch
owned_domain
state_version
state_hash
causal_parent_ids
expires_at | null
```

A02 may assemble only receipts that match the same mission, generation, decision_id and eligibility_epoch.

Mixed-epoch composition is invalid by construction:

```text
ANY receipt.eligibility_epoch != snapshot.eligibility_epoch
=> SNAPSHOT_INVALID
```

## 5. Validation at eligibility time

Eligibility is two-phase:

```text
PHASE 1 = BUILD_SNAPSHOT
PHASE 2 = VALIDATE_CURRENT_AND_COMMIT_ELIGIBILITY
```

At Phase 2, the validator MUST atomically compare every referenced domain version/hash against the current authoritative version for that domain within the G2 mission scope.

```text
CURRENT(readset) == snapshot.readset
AND current_eligibility_epoch == snapshot.eligibility_epoch
AND current_stop_epoch == snapshot.stop_epoch
AND current_fencing_epoch == snapshot.fencing_epoch
AND authority_lease_not_expired
AND authority_lease_not_revoked
```

If any comparison fails:

```text
ELIGIBILITY = HOLD
REASON = STALE_DECISION_SNAPSHOT
ACTION = RECOMPUTE_FROM_CURRENT_FRONTIER
```

There is no implicit carry-forward of a prior PASS/OK/APPROVAL.

## 6. Action eligibility repair

The former abstract conjunction remains semantically valid only when evaluated over one validated snapshot.

```text
ACTION_ELIGIBLE(snapshot) =
    SnapshotCurrent(snapshot)
    AND CognitiveAccept(snapshot)
    AND ConstitutionalOK(snapshot)
    AND SecurityOK(snapshot)
    AND AuthorityValid(snapshot)
    AND RequiredEvidenceOK(snapshot)
    AND NotStopped(snapshot)
```

An `ACTION_ELIGIBLE=true` result MUST emit an immutable `EligibilityReceipt`:

```text
EligibilityReceipt:
    decision_id
    snapshot_id
    readset_hash
    eligibility_epoch
    verdict: ELIGIBLE
    validated_at
    expires_at
    validator_profile_hash
    receipt_hash
```

This receipt is not execution authority.

## 7. Physiology-change eligibility repair

```text
PHYSIOLOGY_CHANGE_ELIGIBLE(snapshot) =
    SnapshotCurrent(snapshot)
    AND ConstitutionalOK(snapshot)
    AND ConstituentCompatible(snapshot)
    AND IndependentAssuranceOK(snapshot)
    AND FounderAuthorizationPresent(snapshot)
```

Founder authorization MUST itself be version-bound in the snapshot. A newer revocation, replacement authorization, STOP or fencing event invalidates the older snapshot.

## 8. Execution binding for any future generation

G2 architecture does not execute external effects. If a later authorized generation introduces an execution boundary, every execution request MUST carry:

```text
snapshot_id
readset_hash
eligibility_epoch
eligibility_receipt_hash
```

The executor MUST revalidate snapshot freshness immediately before effect commit.

```text
STALE_SNAPSHOT_AT_EFFECT_COMMIT => DENY + MUTATION_COUNT_0 + RECOMPUTE_REQUIRED
```

No executor may reconstruct eligibility from historical booleans.

## 9. Invalidation rules

Any dependency-domain mutation emits `ELIGIBILITY_INVALIDATION` for all outstanding snapshots whose read set references the prior version.

Required invalidation triggers:

```text
SECURITY_VERSION_CHANGED
CONSTITUTIONAL_VERSION_CHANGED
EVIDENCE_FRONTIER_CHANGED
COG_ASSURANCE_VERSION_CHANGED
AUTHORITY_REVOKED_OR_VERSION_CHANGED
STOP_EPOCH_CHANGED
FENCING_EPOCH_CHANGED
CONSTITUENT_VERSION_CHANGED
FOUNDER_AUTHORIZATION_VERSION_CHANGED
SYNTHESIS_VERSION_CHANGED
```

Invalidation is monotonic. A snapshot cannot become current again after it is stale.

## 10. Recovery / replacement

Recovery never revives outstanding eligibility implicitly.

On any agent replacement, checkpoint restore or recovery rebinding:

```text
fencing_epoch := fencing_epoch + 1
eligibility_epoch := eligibility_epoch + 1
all outstanding DecisionSnapshot => STALE
```

A decision may proceed only after recomputation from the recovered current frontier.

## 11. Causal provenance

Every versioned prerequisite receipt and every `DecisionSnapshot` preserves immutable `causal_parent_ids`.

The closure of `causal_parent_ids` MUST be acyclic and content-addressed. Snapshot construction cannot drop counterevidence, revocation, STOP or fencing events that causally precede the current domain version.

## 12. A06 cognitive-assurance independence minimum

The prior non-blocking Sýnesis reservation is closed architecturally as follows.

A06 is internal cognitive assurance only, not institutional independent assurance.

Minimum A06 independence:

- separate `AgentInstance` from A03/A04/A05 target-cognition authors;
- separate execution context for the assurance pass;
- A06 MUST NOT author, rewrite or mutate the cognition under review;
- A06 may read target cognition and provenance only through immutable references;
- private mutable working memory is not shared between target-cognition authors and A06;
- shared semantic memory is permitted only through A07 admission with provenance and may not contain hidden target-author scratch state;
- provider/model diversity is RECOMMENDED for epistemic diversity but is not required for internal A06 validity;
- provider/model diversity is insufficient by itself to establish institutional independence;
- external independent assurance remains mandatory for physiology change and cannot be satisfied by A06.

## 13. Terminal invariants

```text
NoMixedEpochEligibility
NoStaleApprovalUse
EligibilityInvalidatedOnDependencyChange
ExecutionRequiresCurrentSnapshot
RecoveryInvalidatesOutstandingEligibility
SnapshotDoesNotGrantAuthority
HANDOFF != AUTHORITY_TRANSFER
CAPABILITY != AUTHORITY
ASSURANCE != PROMOTION
```

This repair changes no L0/G1 identity, authority or historical evidence.