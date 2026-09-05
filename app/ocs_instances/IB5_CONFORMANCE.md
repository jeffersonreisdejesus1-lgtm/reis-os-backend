# IB5 Hazel Continuity / Replacement / Recovery

Implementation scope is limited to mission-scoped instance continuity.

Material criteria:

- Hazel continuity record is authoritative continuity evidence.
- Local registry is a durable projection and cannot override conflicting Hazel state.
- Cold recovery validates profile, authority, namespaces, generation and complete local/Hazel hash agreement.
- Replacement recovery requires exact predecessor lineage and `generation = predecessor + 1`.
- Replacement recovery checks `Hazel.predecessor_hash == predecessor.hazel_event_hash`.
- A Hazel effect already present is read back and reused; it is not emitted again.
- A prepared successor with a durable replacement saga may complete the missing Hazel effect exactly once after restart.
- A local replacement commit with saga still at `READBACK_VERIFIED` is reconciled to `LOCAL_COMMITTED` and `LEASE_FINALIZED` without repeating Hazel or the local commit.
- Persisted lease state must be restored authentically before cold reconciliation.
- More than one ACTIVE generation for the same organization / mission / OCS fails closed.
- Incompatible local/Hazel hashes fail closed.

Epistemic boundary: rejected authority remains `PRE_EFFECT_REJECTION / NO_BINDER_EFFECT`; this slice does not claim a typed `DENY -> MUTATION_COUNT = 0` contract or institutional assurance.
