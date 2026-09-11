# DÉDALA — ARCHITECTURE ASSURANCE

REVIEW_ID
= DEDALA-ARCH-ASSURANCE-AI-MUTATION-ISOLATION-V1-001

TARGET
= NOESIS-META-ARCH-AI-MUTATION-ISOLATION-V1-001

RESULT
= PASS_WITH_RESERVATIONS

ADVERSARIAL FINDINGS
1. Logical gateway alone is insufficient if any AI retains an alternate write credential.
2. Credential broker MUST never disclose raw provider credentials to AI actors.
3. One-shot grants require replay prevention, consumption tracking, TTL, exact target/capability binding and fencing.
4. Unknown provider outcome MUST HOLD; no blind retry.
5. Human break-glass MUST NOT be machine-delegable.
6. Provider-side revocation/downgrade is mandatory before claiming technical impossibility of bypass.
7. Stacked dependency on Authority Gateway V1 must remain explicit.

REQUIRED IMPLEMENTATION CONTROLS
- classify actor as AI vs approved non-AI host executor;
- deny credential materialization to AI actors;
- issue opaque one-shot grants only;
- consume grant exactly once;
- fail closed on mismatch/expiry/replay;
- log denied attempts;
- require provider isolation attestation before activation claim;
- keep MERGE/PROMOTE/DELETE canonical actions outside autonomous grant scope.

BLOCKING HIGH_CRITICAL
= NONE FOR CANDIDATE IMPLEMENTATION

CANONICAL ACTIVATION BLOCKER
= provider credential cutover evidence is mandatory before `AI_DIRECT_MUTATION_TECHNICALLY_BLOCKED = TRUE`.
