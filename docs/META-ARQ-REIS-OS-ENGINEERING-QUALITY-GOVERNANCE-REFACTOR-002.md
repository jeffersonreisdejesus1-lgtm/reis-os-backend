# REIS OS — Meta-Arquitetura v0.2
## Governança, Qualidade, Capability/Seat Registry e Control Plane

DOCUMENT_ID: `META-ARQ-REIS-OS-ENGINEERING-QUALITY-GOVERNANCE-REFACTOR-002`
STATUS: `IMPLEMENTATION_CANDIDATE`
MODE: `ADDITIVE_OVERLAY`

## 1. Material entry state

Preserve the already established runtime and binding semantics. This tranche does not rebuild Kernel, Hazel, Binder, Mission Runtime, Chat Runtime, or Execution Plane.

Current working assumptions for this branch:

- IB7: merged/closed.
- IB8: merged/closed.
- IB9: closed with reservations; PR #55 remains unmerged.
- Chat Runtime boundary: closed with reservations; PR #56 remains draft/unmerged.
- Execution Plane boundary: closed with reservations at `38066eff699662726e1298e6d14256dedc0fa2bc`; PR #57 remains draft/unmerged.
- IB10: not started.
- Command B10 productization: frozen.

## 2. Architectural rule

This refactor is an additive governance overlay.

`RUNTIME_REBUILD = FALSE`

`COMMAND_CONTROL_PLANE = PROJECTION + BOUNDED_CONTROL_SURFACE`

`COMMAND_CONTROL_PLANE != INSTITUTIONAL_SOURCE_OF_TRUTH`

`COMMAND_CONTROL_PLANE != PROMOTION_DECIDER`

`FOUNDER_DECISION = EXPLICIT_FOUNDER_ACT_ONLY`

## 3. Planes

### P0 — Identity & Authority
Preserve. No new authority contract is introduced by this tranche.

### P1 — Execution & Continuity
Preserve. Existing mission/binding/runtime/execution semantics are consumed, not redefined.

### P2 — Evidence & Provenance
Implement typed evidence references, source hashes, observed time, freshness/completeness and claim promotability.

`CLAIM_WITHOUT_EVIDENCE_REF = NON_PROMOTABLE_CLAIM`

### P3 — Quality & Assurance
Implement domain assessments, findings, assurance state and false-PASS resistance.

`VERIFIED != ASSURED`

`ASSURED != APPROVED`

### P4 — Productivity & Learning
Implement diagnostic metrics only. Metrics never create authority, PASS, promotion or Founder approval.

### P5 — Promotion & Founder Decision
Implement readiness derivation and explicit Founder decision records. Readiness may prepare a candidate; it may not release or approve by itself.

### P6 — Capability / Integration / Federated Seat Registry
Replace MCP-centric framing with a broader bounded registry:

- connectors;
- MCP integrations;
- host adapters;
- provider endpoints;
- federated seats;
- read/write/model-invoke capability;
- connection validation;
- source-of-truth role;
- health/freshness;
- machine-verifiable receipt support.

`CAPABILITY != AUTHORITY`

`HOST_LABEL != CONNECTIVITY_PROOF`

### P7 — Control Plane projection
Expose read-only projections for:

- evidence/provenance;
- quality/findings;
- assurance;
- readiness;
- Founder decision status;
- refactor history;
- metrics;
- capability/integration/seat health.

The projection may issue bounded control requests only through existing authority-bearing services. It cannot mutate canonical mission/identity/authority state directly.

## 4. Gate architecture

`G0 = EXECUTION`

`G1 = TECHNICAL_QUALITY`

`G2 = INDEPENDENT_ASSURANCE_IF_REQUIRED`

G2 may combine technical adversarial assurance, institutional assurance and federated cross-seat assurance according to policy. Assurance does not transfer authority.

`G3 = PROMOTION_READINESS`

`G4 = FOUNDER_APPROVAL`

No micro-gate explosion.

## 5. Source-of-truth boundaries

- Mission/authority/identity: existing institutional runtime stores/contracts.
- Execution-local state: Execution Plane bounded execution ledger.
- Governance records: additive Governance Ledger introduced by this tranche.
- Capability/seat inventory: bounded Capability Registry introduced by this tranche.
- Control Plane: projection only over the above sources.

No store in this tranche may silently become a replacement mission or authority SoR.

## 6. Anti-Goodhart rules

- no single metric promotes;
- no aggregate score produces PASS;
- unknown remains UNKNOWN;
- missing source ref makes a claim non-promotable;
- low elapsed time does not reward premature closure;
- low retries do not reward hidden retries;
- low Founder intervention does not reward failure to escalate.

## 7. Stop conditions

Stop if any of the following appears:

- runtime lifecycle redesign is required without a material falsifier;
- Command projection mutates canonical authority/mission state;
- metric or score creates PASS/promotion;
- Founder approval is inferred rather than explicit;
- a connector/plugin/host label is treated as proven capability;
- capability write/model invocation occurs without authority and receipt/readback;
- a new parallel mission/authority SoR is introduced;
- micro-handoff dependency is introduced.

## 8. Product boundary

This tranche implements governance and Control Plane backend contracts/projections only.

`COMMAND_B10_PRODUCTIZATION = FROZEN`

UI/productization remains a later explicit Founder-authorized phase.
