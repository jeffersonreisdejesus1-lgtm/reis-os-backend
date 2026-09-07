# REIS OS Execution Plane — Meta-Architecture

## Mission
Materialize the execution substrate below the REIS OS chat/command runtime so OCS peers, auxiliaries, task specialists and federated correspondents can be instantiated, fenced, replaced and invoked without relying on native same-tab model spawning.

## Layers

`CHAT / WORK / COMMAND`
→ `REIS_OS_CHAT_RUNTIME`
→ `REIS_OS_EXECUTION_PLANE`
→ `INSTANCE MANAGER / AUXILIARY MANAGER / FEDERATED CORRESPONDENT MANAGER`
→ `HOST ADAPTER / WORKER FACTORY REGISTRY`
→ `LOCAL OR REMOTE WORKERS / PROVIDER ADAPTERS`

## Identity grammar

- OCS = institutional identity.
- INSTANCE = material operational binding.
- HOST = execution seat.
- PROVIDER = model/worker provider behind a host.
- CORRESPONDENT = instance of an existing OCS on another host.
- AUXILIARY = temporary worker subordinated to its parent OCS.
- TASK_SPECIALIST = temporary auxiliary with narrower task scope.

`HOST != OCS`
`MODEL != OCS`
`AUXILIARY_CREATION_DOES_NOT_CREATE_A_NEW_OCS`
`AUXILIARY_AGENT_AUTHORITY ⊆ PARENT_OCS_MISSION_AUTHORITY`

## Material lifecycle

`MATERIALIZE → ACTIVE → EXECUTE → RECEIPT`

Replacement:
`ACTIVE(gen N) → FENCED → MATERIALIZE(gen N+1) → ACTIVE`

Old generations cannot dispatch once fenced.

## Internal communication

A source instance can dispatch to another bound OCS instance through the execution plane, subject to authority policy and target availability.

## Federated communication

The same OCS may have distinct correspondents on GPT, GROK, CLAUDE or another host, provided each binding has explicit host/provider/instance/generation/authority metadata.

Provider connectivity itself remains adapter-dependent. Naming a host never proves connectivity.

## Same-surface operation

The visible chat surface does not need to physically host multiple agents. It can remain the command surface while execution occurs in workers managed by this plane and receipts return to the same mission.

## Durability

SQLite-backed instance registry and execution receipts provide durable material identity, fencing state and idempotent readback. The chat transcript is not the source of truth.

## Non-claims

- No native ChatGPT same-tab spawn is claimed.
- No Grok/Claude API connectivity is claimed without a real provider adapter.
- No provider access is fabricated by this layer.
- No IB10 or Command B10 behavior is started.
