# NOESIS META-ARCHITECTURE — AI MUTATION ISOLATION V1

ARCHITECTURE_ID
= NOESIS-META-ARCH-AI-MUTATION-ISOLATION-V1-001

MISSION_ID
= REIS-AI-MUTATION-ISOLATION-V1-001

CLASS
= INSTITUTIONAL_EXECUTION_CONTROL_PLANE

OBJECTIVE
= Make direct external mutation by any AI system technically unavailable outside the REIS OS governed execution path.

CORE_INVARIANTS
- AI_CAPABILITY != EXECUTION_AUTHORITY
- NO_AUTHORITY_PROOF -> NO_CREDENTIAL -> NO_MUTATION
- DIRECT_AI_PROVIDER_MUTATION = FORBIDDEN
- DEFAULT = FAIL_CLOSED
- READ_ONLY may remain available when separately permitted

SCOPE — AI ACTORS
- ChatGPT sessions
- REIS OS OCSs
- Codex
- Claude
- Gemini
- Grok
- Copilot
- Replit Agent
- internal/custom agents
- any future AI/model/runtime capable of provider access

SCOPE — PROVIDERS
- GitHub
- Render
- Vercel
- Cloud providers
- CI/CD systems
- other institutional mutation-capable providers

MANDATORY PATH
AI / OCS / AGENT
-> ORCHESTRATOR
-> UNIVERSAL KERNEL
-> AUTHORITY GATEWAY
-> CREDENTIAL BROKER
-> APPROVED HOST EXECUTOR
-> PROVIDER
-> EFFECT RECEIPT
-> EVIDENCE LEDGER
-> RECONCILIATION

DIRECT PATH
AI / OCS / AGENT -> PROVIDER
= FORBIDDEN

AUTHORIZATION CONTRACT
Every mutation request must bind:
- canonical_identity
- mission_id
- orchestrator_run_id
- mission_stage
- authority_ref
- delegation_ref
- target
- capability
- payload_ref/surface
- generation
- fencing_epoch
- evidence_parent
- issued_at
- expires_at
- founder_approval_ref when required
- zero-spend decision when applicable

CREDENTIAL MODEL
1. AI actors MUST NOT receive long-lived provider write credentials.
2. Provider write credentials MUST be held only by an approved non-AI execution boundary.
3. The broker issues no raw credential to an AI actor.
4. The broker may issue only a one-shot execution grant bound to one request, target, capability and TTL.
5. Provider credentials are used only inside the approved host executor after authority validation.
6. Unknown, stale, replayed or mismatched grants are denied.

ACTION CLASSES
A — READ_ONLY: inspect/search/logs; no mutation.
B — BOUNDED_MUTATION: create branch, write/update file, open/update PR, deploy staging.
C — SENSITIVE_MUTATION: infra config, secret rotation, destructive staging action.
D — FOUNDER_ONLY: merge main, promote production, delete canonical resource, expand authority/policy.

AI MUTATION RULE
Even a canonical OCS cannot directly perform B/C/D actions. It can request them through the governed path only.

ANTI-BYPASS REQUIREMENT
Absolute enforcement is not proven until:
- all direct AI write credentials/connectors are revoked or downgraded to read-only;
- only the approved host executor retains mutation credentials;
- provider-side permissions prevent alternate mutation paths;
- break-glass is human-only, explicit, time-bounded, logged and not delegated to AI.

ANTI-REPLAY
- request_id + nonce/fingerprint uniqueness
- one-shot grant
- TTL
- consumed-state tracking
- generation/fencing validation
- no blind retry after unknown outcome

EVIDENCE
Record both allow and deny decisions:
- AUTHORITY_DECISION
- EFFECT_INTENT
- EFFECT_RESULT
- PROVIDER_RECEIPT
- RECONCILIATION

ROLLOUT PHASES
P0 architecture + assurance.
P1 broker/isolation software candidate.
P2 negative/positive qualification.
P3 provider credential inventory and cutover plan.
P4 revoke/downgrade direct AI write access.
P5 activate broker-only mutation path.
P6 adversarial bypass test.
P7 Founder final gate for canonical activation.

PROMOTION CONDITION
Canonical claim `AI_DIRECT_MUTATION_TECHNICALLY_BLOCKED = TRUE` is forbidden until P4-P6 are externally evidenced.

DEPENDENCY
This candidate is stacked on REIS Authority Gateway V1 / PR #99 and MUST NOT be promoted ahead of that dependency.
