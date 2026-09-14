# OCS-X G2 Constitutional Multi-Agent Architecture

OBJECT = OCSX-G2-MULTIAGENT-CONSTITUTIONAL-ARCHITECTURE-001
MISSION = REIS-OS-OCSX-PHYSIOLOGICAL-EXPERIMENTAL-LINEAGE-001
HANDOFF = NOESIS-TO-DEDALA-OCSX-G2-MULTIAGENT-ARCHITECTURE-001
ARCHITECT = DÉDALA
STATE = ARCHITECTURE_CANDIDATE_ONLY
IMPLEMENTATION = NOT_AUTHORIZED

## 0. Generational boundary

G0 = ancestral L0 identity, ancestry and inherited authority ceiling.
G1 = G0 + qualified L1 physiological mechanism.
G2 = G0 + G1 + new L2 constitutional multi-agent mesh.

G2 is strictly additive. It MUST NOT reinterpret, overwrite or invalidate historical G0/G1 evidence.

Frozen inheritance:
- L0_PROFILE_ID = L0_FROZEN_V1
- L0 identity / ancestry / authority ceiling remain immutable.
- G1 single effective writer, single terminal stop, stop fencing, recovery binding and UNKNOWN fail-closed semantics remain historically valid for G1.
- L2 may introduce domain-partitioned ownership only inside G2 and only under the rules below.

Core invariants:

`PI != AGENT`

`ONE_AGENT_PER_PI = PROHIBITED_AS_DEFAULT`

`AGENT_EXISTS IFF SEPARATION_VALUE > COORDINATION_COST`

`OCS_IDENTITY != AGENT_IDENTITY`

`AGENT != AGENT_INSTANCE`

`NAME != IDENTITY`

`ID != AUTHORITY`

`ROLE != AUTHORITY`

`CAPABILITY != AUTHORITY`

`HANDOFF != AUTHORITY_TRANSFER`

`CONSTITUENT_GUARDIAN != CONSTITUENT_POWER`

`SELF_HOMOLOGATION = FORBIDDEN`

No L2 actor is sovereign. No internal actor may create institutional authority, promote the organism, mutate OURO, write cross-OCS canonical state, or redefine L0/G1.

---

## 1. Minimal non-redundant roster

The candidate roster is deliberately smaller than the list of possible roles. Functional roles are clustered where separation does not materially improve independence, authority isolation, recovery or observability.

| Agent identity class | Primary role | Clustered responsibilities | Why autonomous |
|---|---|---|---|
| A01 ORDERING | deterministic ordering/scheduler | ready-set ordering, bounded fairness, stop/no-progress scheduling | independent lifecycle and formal-verification value |
| A02 COORDINATION | coordination + orchestration | dependency/rendezvous, dispatch envelope assembly, aggregation, bounded retry/escalation | asynchronous coordination and fault isolation |
| A03 COG-PRIMARY | primary cognition | candidate reasoning/proposal generation | primary cognitive state |
| A04 COG-CRITIC | alternative + critic | alternative hypotheses, contradiction search, adversarial challenge | epistemic independence |
| A05 COG-SYNTHESIS | evidence analysis + synthesis | evidence-weighted synthesis, unresolved-conflict representation | independent aggregation/provenance boundary |
| A06 COG-ASSURANCE | cognitive assurance | independent falsification of synthesized cognition | self-homologation prevention |
| A07 MEMORY | memory governance cluster | working + episodic + semantic admission/retrieval, provenance-integrity enforcement | memory poisoning/recovery isolation |
| A08 CONSTITUTIONAL | constitutional guardian | inherited constraint checks, HOLD/DENY/ESCALATE | distinct veto boundary |
| A09 SECURITY | cybersecurity sentinel | tool, secret, namespace, injection, effect, supply-chain controls | distinct permission boundary |
| A10 TECH-INDEP | technological-independence sentinel | provider/model/host portability, fallback/substitutability/capture risk | independent provider-dependency check |
| A11 EVIDENCE | evidence/provenance steward | claim/source/agent/transformation lineage, evidence ledger | independent auditability |
| A12 RECOVERY | recovery/continuity steward | checkpoint, fencing, rebinding, replacement, stop preservation | independent recovery control |
| A13 CONSTITUENT | constituent guardian | organism-continuity validation and Founder escalation | constitutive independence |

Roster size = 13 bounded agent identities.

The following are NOT separate agents in G2 candidate v1:
- separate scheduler and ordering agents: merged into A01;
- separate coordinator and orchestrator: merged into A02;
- separate alternative reasoner and critic: merged into A04;
- separate evidence analyst and synthesizer: merged into A05;
- separate working/episodic/semantic memory agents: clustered under A07 with typed sub-stores and separate admission policies.

A future split requires evidence that separation value exceeds coordination cost.

---

## 2. Identity contracts

### 2.1 AgentIdentity

```text
AgentIdentity:
    agent_id: string
    ocs_id: string
    layer: "L2"
    generation: string
    role: enum
    domain: string
    governed_pi_set: set<PI_ID>
    authority_ceiling_ref: string
    authority_ceiling_hash: sha256
    allowed_actions: set<ActionType>
    forbidden_actions: set<ActionType>
    owned_state_domains: set<StateDomain>
    memory_namespace: string
    evidence_namespace: string
    tool_allowlist: set<ToolCapabilityRef>
    communication_permissions: set<MessageRoute>
    escalation_target: enum{CONSTITUTIONAL,CONSTITUENT,FOUNDER,EXTERNAL_ASSURANCE}
    lifecycle_policy_ref: string
    profile_version: integer
    profile_hash: sha256
```

`profile_hash` binds at minimum role, governed PI set, authority ceiling, actions, owned state domains, memory namespace, evidence namespace, tool allowlist, communication permissions and lifecycle policy.

Any mismatch between expected profile hash and presented profile hash => `AGENT_PROFILE_DRIFT -> FENCE`.

### 2.2 AgentInstance

```text
AgentInstance:
    agent_instance_id: string
    agent_id: string
    ocs_id: string
    mission_id: string
    generation: string
    profile_hash: sha256
    authority_snapshot_hash: sha256
    status: enum{CREATED,BOUND,READY,RUNNING,WAITING,HOLD,STOPPED,FENCED,FAILED,REPLACED}
    last_checkpoint_ref: string | null
    predecessor_instance_id: string | null
    fencing_epoch: integer
    started_at: timestamp
    stopped_at: timestamp | null
```

Identity pattern:
`OCSX::L2::AGT::<ROLE>::<NNN>`

Instance pattern:
`OCSX::L2::INST::<AGENT_ID_SHORT>::<GENERATION>::<NNN>`

`AGENT_INSTANCE_ID` never grants authority. A replacement instance inherits only a validated authority snapshot and current fencing epoch.

---

## 3. PI → agent-cluster responsibility matrix

The 36-PI topology remains physiological. G2 maps coherent PI responsibilities to clusters rather than creating one agent per PI.

| PI responsibility family | Primary agent | Secondary/checking agent |
|---|---|---|
| ordering, scheduling, fairness, stop progression | A01 ORDERING | A08 CONSTITUTIONAL, A12 RECOVERY |
| decomposition, dispatch, dependency, rendezvous, retry | A02 COORDINATION | A01 ORDERING, A09 SECURITY |
| primary inference/proposal formation | A03 COG-PRIMARY | A04 COG-CRITIC |
| alternative hypothesis, contradiction, adversarial cognition | A04 COG-CRITIC | A06 COG-ASSURANCE |
| evidence weighting, synthesis, conflict representation | A05 COG-SYNTHESIS | A11 EVIDENCE, A06 COG-ASSURANCE |
| cognitive falsification / no-self-homologation | A06 COG-ASSURANCE | A11 EVIDENCE |
| working/episodic/semantic memory admission and retrieval | A07 MEMORY | A11 EVIDENCE, A09 SECURITY |
| inherited constitutional constraints and authority compatibility | A08 CONSTITUTIONAL | A13 CONSTITUENT |
| tools/effects/secrets/namespace/security | A09 SECURITY | A08 CONSTITUTIONAL |
| provider/model/host portability and capture exposure | A10 TECH-INDEP | A09 SECURITY |
| evidence ledger/provenance/counterevidence | A11 EVIDENCE | A06 COG-ASSURANCE |
| checkpoint/recovery/rebinding/fencing | A12 RECOVERY | A08 CONSTITUTIONAL, A09 SECURITY |
| constitutive organism continuity | A13 CONSTITUENT | Founder external authority |

A PI may be observed or checked by multiple agents but has exactly one primary G2 responsibility owner for mutable L2 state.

---

## 4. Typed communication graph

Unconstrained all-to-all chat is prohibited.

### 4.1 Message envelope

```text
AgentMessage:
    message_id
    mission_id
    source_agent_id
    source_instance_id
    source_profile_hash
    destination_agent_id | destination_role
    message_type
    payload_ref
    evidence_refs[]
    authority_ref | null
    causal_parent_ids[]
    created_at
    expires_at | null
    integrity_hash
```

Allowed message types:
- `WORK_PROPOSAL`
- `WORK_ASSIGNMENT`
- `COGNITIVE_CANDIDATE`
- `COGNITIVE_CHALLENGE`
- `EVIDENCE_REQUEST`
- `EVIDENCE_RESPONSE`
- `SYNTHESIS_CANDIDATE`
- `ASSURANCE_FINDING`
- `CONSTITUTIONAL_FINDING`
- `SECURITY_FINDING`
- `TECH_DEPENDENCY_FINDING`
- `MEMORY_ADMISSION_REQUEST`
- `MEMORY_RETRIEVAL_RESPONSE`
- `CHECKPOINT_REQUEST`
- `RECOVERY_BINDING`
- `STOP_SIGNAL`
- `ESCALATION`

### 4.2 Allowed high-level routes

- A01 ↔ A02 for scheduling/readiness only.
- A02 → A03/A04 for bounded cognitive assignments.
- A03/A04 → A05 for candidate/challenge material.
- A05 → A06 for independent cognitive assurance.
- A03/A04/A05/A06 ↔ A11 for evidence references only.
- all agents → A07 only through typed memory admission/retrieval.
- all effect-capable requests → A09 SECURITY before eligibility.
- all action/physiology eligibility → A08 CONSTITUTIONAL.
- provider-dependent route changes → A10 TECH-INDEP review.
- recovery/replacement → A12 RECOVERY with A08/A09 validation.
- physiology/identity-continuity questions → A13 CONSTITUENT.
- A13 → Founder only through `REQUIRES_FOUNDER` escalation.

Prohibited:
- direct A03/A04 self-approval;
- A05 rewriting source proposals;
- A06 modifying cognition under review;
- A07 authorizing action;
- A11 fabricating source authority;
- A09 executing mission effects merely because security approved;
- A08 creating authority;
- A13 exercising constituent power.

---

## 5. State ownership and writer model

G1 historical guarantee remains `SINGLE_WRITER` for the G1 runtime.

G2 candidate uses:

`SINGLE_WRITER_PER_OWNED_STATE_DOMAIN`

This is NOT a retroactive relaxation of G1.

State domains:

| State domain | Sole writer |
|---|---|
| `schedule_state` | A01 |
| `coordination_state` | A02 |
| `primary_cognition_state` | A03 |
| `critic_state` | A04 |
| `synthesis_state` | A05 |
| `cognitive_assurance_state` | A06 |
| `memory_index_state` | A07 |
| `constitutional_findings_state` | A08 |
| `security_findings_state` | A09 |
| `tech_independence_state` | A10 |
| `evidence_ledger_state` | A11 |
| `recovery_state` | A12 |
| `constituent_findings_state` | A13 |

No agent may mutate another domain. Cross-domain updates occur only by immutable typed messages/events.

Conflict rule:
`TWO_VALID_WRITERS_SAME_DOMAIN_SAME_EPOCH -> FENCE_BOTH + RECOVERY_RECONCILIATION`

Canonical/OURO writes remain forbidden to all L2 agents.

---

## 6. Memory governance

A07 is one agent with four internal typed stores, not four autonomous agents:
- working;
- episodic;
- semantic;
- provenance-integrity index.

Memory admission requires:

`ADMIT = ELIGIBLE_TYPE AND SOURCE_BOUND AND PROVENANCE_BOUND AND INTEGRITY_OK AND POLICY_OK`

Rules:
- persisted memory != truth;
- retrieved memory carries source/evidence/age/profile lineage;
- stale memory MUST remain stale;
- contradicted memory is retained with counterevidence, not silently overwritten;
- synthetic/derived/observed/verified/assured classes remain distinct;
- memory cannot grant authority or tool permission;
- agent-private working memory cannot be promoted to shared semantic memory without admission receipt;
- cross-OCS memory writes are forbidden.

Memory receipt minimum:
`memory_item_id, class, source_agent_id, source_instance_id, source_profile_hash, evidence_refs, transformation_ref, admitted_by, admitted_at, freshness, contradiction_refs, integrity_hash`.

---

## 7. Authority ceiling and forbidden-action matrix

All L2 agents inherit the same institutional ceiling: no new authority beyond validated external/L0 authority.

| Agent | May HOLD | May DENY | May execute external effect | May canonical write | May create authority | May self-promote |
|---|---:|---:|---:|---:|---:|---:|
| A01 | scheduling only | no | no | no | no | no |
| A02 | coordination only | no | no | no | no | no |
| A03 | no | no | no | no | no | no |
| A04 | cognitive challenge | no | no | no | no | no |
| A05 | unresolved-conflict HOLD | no | no | no | no | no |
| A06 | cognitive assurance HOLD | cognitive candidate only | no | no | no | no |
| A07 | memory admission HOLD | memory admission only | no | no | no | no |
| A08 | yes | yes within constitutional policy | no | no | no | no |
| A09 | yes | yes within security policy | no | no | no | no |
| A10 | dependency HOLD | no | no | no | no | no |
| A11 | evidence sufficiency HOLD | no | no | no | no | no |
| A12 | recovery HOLD | fence invalid instance | no | no | no | no |
| A13 | yes | constitutional-invalid only | no | no | no | no |

Effect execution, if ever authorized in a future generation, must remain a separate execution boundary outside these architecture claims.

---

## 8. Tool/capability model

Each AgentIdentity owns a static tool allowlist bound into `profile_hash`; each mission supplies a narrower lease.

Effective tools:
`EFFECTIVE_TOOLS = PROFILE_ALLOWLIST ∩ MISSION_LEASE ∩ SECURITY_APPROVAL`

Empty intersection is valid and must fail closed.

Tool request must bind:
`agent_id, instance_id, profile_hash, mission_id, tool_ref, action, target, authority_ref, evidence_ref, idempotency_key, expiry`.

A09 validates security, but approval does not execute. A08 validates constitutional compatibility. External effect execution remains out of scope for G2 architecture.

---

## 9. Quorum, veto and degraded mode

No supreme internal agent exists.

### 9.1 Cognitive acceptance

```text
COGNITIVE_ACCEPT =
    SYNTHESIS_PRESENT
    AND EVIDENCE_MINIMUM_MET
    AND COG_ASSURANCE != BLOCKING
    AND UNRESOLVED_CONTRADICTION != BLOCKING
```

The primary and critic do not vote numerically. They contribute separately provenance-bound material. A05 synthesizes; A06 independently challenges.

### 9.2 Action eligibility

```text
ACTION_ELIGIBLE =
    COGNITIVE_ACCEPT
    AND CONSTITUTIONAL_OK
    AND SECURITY_OK
    AND AUTHORITY_REF_VALID
    AND REQUIRED_EVIDENCE_OK
    AND NOT_STOPPED
```

### 9.3 Physiology-change eligibility

```text
PHYSIOLOGY_CHANGE_ELIGIBLE =
    CONSTITUTIONAL_OK
    AND CONSTITUENT_COMPATIBLE
    AND INDEPENDENT_ASSURANCE_OK
    AND FOUNDER_AUTHORIZATION_PRESENT
```

No L2 agent can satisfy `FOUNDER_AUTHORIZATION_PRESENT` by itself.

### 9.4 Veto classes

Hard veto:
- L0/profile drift;
- authority expansion;
- forbidden namespace/effect;
- security-critical violation;
- constituent invalidity;
- evidence integrity failure;
- stop/fencing violation.

Soft HOLD:
- unavailable critic/assurance;
- stale evidence;
- unresolved contradiction;
- provider-capture risk without fallback;
- incomplete provenance.

### 9.5 Degraded mode

- A03 unavailable: no new cognitive candidate; existing verified evidence may remain readable.
- A04 unavailable: cognition may be generated but cannot become `COGNITIVE_ACCEPT` where adversarial independence is required.
- A05 unavailable: no synthesis; no action eligibility.
- A06 unavailable: no assured cognition; may remain proposal/HOLD.
- A07 unavailable: no new persistent memory admission; volatile bounded operation may continue only if mission allows.
- A08 unavailable: action eligibility = FALSE.
- A09 unavailable: tool/effect eligibility = FALSE.
- A10 unavailable: provider-dependent migration/change = HOLD; provider-neutral local reasoning may continue if otherwise allowed.
- A11 unavailable: no stronger evidence class; action requiring evidence = HOLD.
- A12 unavailable: no instance replacement/recovery; existing healthy instances may continue until checkpoint/recovery obligation arises.
- A13 unavailable: physiology/identity-affecting change = REQUIRES_FOUNDER/HOLD.

---

## 10. Stop, no-progress, deadlock, livelock and fencing

G2 inherits G1 stop semantics and makes them mesh-wide.

Global terminal state is written only by A01 from a valid terminal event and becomes immutable for the generation.

Terminal reasons include inherited G1 reasons plus:
- `DEADLOCK`
- `LIVELLOCK`
- `QUORUM_UNAVAILABLE`
- `PROFILE_DRIFT`
- `SECURITY_ABORT`
- `CONSTITUENT_INVALID`

No-progress monitor:
- progress requires externally defined material progress evidence, not message count;
- coordination chatter, retries and repeated equivalent cognition do not count as progress;
- bounded no-progress window expiry => HOLD or STOP according to preregistered mission policy.

Deadlock detection candidate:
`all READY/RUNNING-capable agents are WAITING AND wait-for graph has cycle AND no admissible external event can break cycle`.

Livelock detection candidate:
`state keeps transitioning but material-progress metric unchanged for N bounded epochs`.

After global STOP:
- no agent may transition to RUNNING;
- no new writer lease may be issued;
- all late messages are ignored or archived as post-stop evidence;
- recovery must preserve STOP.

Fencing epoch is monotonic. Only the highest validated epoch may write an owned state domain.

---

## 11. Recovery and replacement

A12 owns recovery metadata but does not grant authority.

Replacement protocol:
1. detect failed/stale/fenced instance;
2. freeze old instance writer lease;
3. validate OCS identity and L0 binding;
4. validate AgentIdentity profile hash;
5. validate authority snapshot hash and mission lease freshness;
6. validate namespace and last checkpoint integrity;
7. preserve global STOP/terminal state;
8. increment fencing epoch;
9. create successor instance with predecessor reference;
10. emit `RECOVERY_BINDING` receipt;
11. only then allow READY/RUNNING.

Any mismatch => FENCED + escalation.

`RECOVERY != AUTHORITY_REISSUANCE`

---

## 12. Security architecture

A09 threat surfaces:
- prompt/instruction injection;
- tool misuse;
- secret leakage;
- cross-namespace access;
- confused deputy;
- stale/forged authority references;
- supply-chain/model/plugin compromise;
- malicious evidence payloads;
- lateral agent-message spoofing;
- replay/idempotency failure;
- privilege laundering through coordinator;
- exfiltration via memory/provenance fields.

Controls:
- signed/hashed typed envelopes;
- profile-bound allowlists;
- mission-scoped leases;
- explicit target namespace;
- immutable provenance refs;
- anti-replay/idempotency keys;
- fail-closed unknown permissions;
- no raw all-to-all channel;
- security approval separated from execution;
- output/data classification before tool dispatch.

---

## 13. Technological independence

A10 continuously emits dependency records:

```text
TechnologyDependency:
    dependency_id
    provider
    model_or_runtime
    capability_used
    physiological_criticality
    substitutable
    tested_fallback_refs[]
    migration_cost_class
    data_portability
    protocol_portability
    observed_lock_in
    last_verified_at
```

Rules:
- no single provider may become implicit identity, authority or source of truth;
- provider/model replacement must not require L0 identity mutation;
- critical capability with no tested fallback => explicit HOLD/risk, never hidden;
- evidence formats and internal message contracts remain provider-neutral;
- model-specific cognition remains opaque behind bounded agent contracts.

---

## 14. Constitutional vs constituent guardians

A08 CONSTITUTIONAL answers:
`Is this proposed action/physiology behavior permitted by the currently inherited constitution and authority envelope?`

Outputs:
`CONSTITUTIONAL_OK | CONSTITUTIONAL_HOLD | CONSTITUTIONAL_DENY | ESCALATE`

A13 CONSTITUENT answers:
`Would this change preserve the identity/constitutive continuity of the same authorized OCS-X organism?`

Outputs:
`CONSTITUTIONALLY_VALID | CONSTITUTIONALLY_INVALID | REQUIRES_FOUNDER`

A08 cannot rewrite constitution.
A13 cannot exercise constituent power.
Founder/superior REIS OS constitutional authority remains external.

---

## 15. Telemetry and evidence

Every material event must permit reconstruction of who did what, under which identity/profile/authority/evidence, and with which result.

```text
AgentEvent:
    event_id
    mission_id
    ocs_id
    generation
    agent_id
    agent_instance_id
    agent_profile_hash
    fencing_epoch
    event_type
    input_message_ids[]
    evidence_refs[]
    authority_ref | null
    tool_ref | null
    target_namespace | null
    owned_state_domain | null
    previous_state_hash | null
    result_state_hash | null
    outcome
    denial_or_hold_reason | null
    causal_parent_ids[]
    timestamp
    integrity_hash
```

Required global trace properties:
- causal parent closure;
- no event attributed to unknown agent/profile;
- no state-domain mutation by non-owner;
- no accepted event from stale fencing epoch;
- no assurance event authored by the cognition it assures;
- no evidence strength greater than source evidence permits;
- counterevidence remains linkable.

---

## 16. Threat model

| Threat | Required architectural response |
|---|---|
| collusion among cognitive agents | A06 independence + A11 immutable provenance + external assurance option |
| circular validation | assurance cannot cite only outputs derived from target cognition; provenance DAG cycle check |
| authority laundering | authority refs cannot be created/transferred by messages/handoffs |
| memory poisoning | typed admission, source class, contradiction retention, provenance integrity |
| stale identity/profile | profile hash + version + fencing before work/write |
| confused deputy | explicit requester/authority/target/tool binding |
| rogue tool use | allowlist ∩ lease ∩ security approval; no implicit tools |
| Byzantine/contradictory agents | contradiction surfaced, no majority-by-count truth, HOLD on blocking conflict |
| cascade failure | degraded-mode matrix and state-domain fault isolation |
| coordination explosion | bounded routes, 13-agent cap candidate, message budgets, no all-to-all |
| provider capture | A10 dependency ledger + tested fallback requirement |
| recovery split brain | monotonic fencing epochs and single writer per domain |
| self-homologation | A06 cannot be target cognition author; external independent assurance for physiology change |
| guardian capture | no guardian creates authority; Founder escalation remains external |

---

## 17. G1 vs G2 experimental plan

Goal: measure whether G2 separation provides material benefit over qualified G1 without rewriting historical G0/G1 results.

Paired design:
- same preregistered task families and evidence inputs;
- G1 executes qualified L1 baseline;
- G2 executes L1 + L2 mesh candidate;
- freeze task order/random seeds/provider versions where applicable;
- preserve independent receipts and exact artifact hashes;
- no cross-condition memory leakage.

Primary comparison axes:
1. task correctness / accepted outcome;
2. invariant violations;
3. unsupported-claim rate;
4. evidence/provenance completeness;
5. authority/security denials correctly triggered;
6. recovery success / split-brain prevention;
7. deadlock/livelock incidence;
8. latency;
9. model/tool calls;
10. message count / coordination cost;
11. provider-fallback success;
12. independent-assurance disagreement rate;
13. stop/no-progress correctness.

Decision rule is not `G2 wins if smarter`.

G2 architectural value requires a preregistered net benefit:
`SAFETY + TRACEABILITY + RECOVERY + COGNITIVE_QUALITY_GAIN > COORDINATION_COST + LATENCY + FAILURE_SURFACE`.

No G2 result may retroactively modify G1 qualification evidence.

---

## 18. Formal-verification projection candidates

LLM cognition content remains opaque. Formal models cover control-plane semantics only.

Candidates:
- G2-SCHED: scheduler ready/wait/stop/fairness/no-progress model;
- G2-OWN: single-writer-per-domain ownership and fencing;
- G2-MSG: typed communication routing and prohibited edges;
- G2-QUORUM: cognitive/action/physiology eligibility and unavailable-agent degraded modes;
- G2-REC: recovery, predecessor lineage, epoch monotonicity and STOP preservation;
- G2-AUTH: authority non-creation/non-transfer through handoff/messages;
- G2-ASSURE: self-homologation prohibition and provenance independence;
- G2-DEAD: wait-for deadlock/livelock bounded termination properties.

Expected safety properties:
- `NoCrossDomainWrite`
- `NoStaleEpochWrite`
- `NoPostStopReentry`
- `NoAuthorityCreation`
- `NoHandoffAuthorityTransfer`
- `NoSelfHomologation`
- `NoConstituentPowerInsideMesh`
- `NoActionWithoutRequiredEligibility`

Expected liveness properties under explicitly stated fairness/availability assumptions:
- `EligibleWorkEventuallyRunsOrStops`
- `DeadlockEventuallyDetected`
- `ReplacementEventuallyFencesPredecessor`
- `GlobalStopEventuallyStable`

Formal PASS never implies LLM correctness.

---

## 19. Theory of done for G2 architecture

G2 architecture is complete enough for independent architecture assurance only when all conditions are met:

1. G0/G1 frozen boundaries are explicit and unmodified.
2. Minimal roster is justified against separation-value criterion.
3. AgentIdentity and AgentInstance contracts are complete.
4. Every PI responsibility family maps to a bounded cluster/owner.
5. Communication graph is typed and non-all-to-all.
6. Every mutable L2 state domain has exactly one writer per fencing epoch.
7. Memory admission/retrieval/provenance rules are explicit.
8. Per-agent authority ceilings/forbidden actions are explicit.
9. Tool allowlist/mission lease/security intersection is explicit.
10. Cognitive/action/physiology eligibility rules are explicit.
11. Veto, degraded-mode and unavailable-agent semantics are explicit.
12. Stop/no-progress/deadlock/livelock/fencing rules are explicit.
13. Recovery preserves identity/profile/authority/namespace/STOP and prevents split brain.
14. Cybersecurity and technological-independence controls are explicit.
15. Constitutional and constituent guardians are separated and Founder escalation is external.
16. Telemetry reconstructs actor/profile/evidence/authority/causality/result.
17. Threat model covers the mandated adversarial classes.
18. G1-vs-G2 experimental plan is preregisterable and does not rewrite history.
19. Formal-projection candidates state both safety and liveness targets.
20. No implementation, merge, promotion, production, OURO access or canonical mutation is authorized by the architecture artifact.

Architecture disposition values:
- `INCOMPLETE`
- `READY_FOR_NOESIS_CONSOLIDATION`
- `READY_FOR_INDEPENDENT_ARCHITECTURE_ASSURANCE`

This artifact's candidate disposition:
`READY_FOR_NOESIS_CONSOLIDATION`

## Governance boundary

ARCHITECTURE != IMPLEMENTATION
IMPLEMENTATION != EVIDENCE
EVIDENCE != ASSURANCE
ASSURANCE != PROMOTION

OCS_X_G2_IMPLEMENTATION = NOT_AUTHORIZED
PRODUCTION_ROUTING = FORBIDDEN
CANONICAL_STATE_WRITE = FORBIDDEN
OURO_ACCESS = FORBIDDEN
KERNEL_AUTHORITY_MUTATION = FORBIDDEN
MERGE = NOT_AUTHORIZED
PROMOTION = NOT_AUTHORIZED
UNIVERSAL_ROLLOUT = NOT_AUTHORIZED
