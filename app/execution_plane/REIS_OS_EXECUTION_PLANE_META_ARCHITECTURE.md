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

Direct auxiliary/task-specialist materialization must inherit parent mission, OCS identity, host/provider, authority reference, state namespace, memory namespace and lease. A caller cannot construct a foreign-OCS auxiliary by supplying a parent pointer alone.

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

## Durability and source-of-truth boundary

SQLite-backed execution records provide durable instance/worker lifecycle state, fencing state, execution receipts and idempotent readback for this plane.

This store is a **bounded execution ledger**, not a replacement institutional source of truth for mission authority or canonical OCS binding.

`EXECUTION_PLANE_STORE != INSTITUTIONAL_AUTHORITY_SOR`

`EXECUTION_PLANE_STORE != MISSION_JOURNAL`

`COMMAND != SOURCE_OF_TRUTH`

Canonical mission/authority/binding semantics remain governed by their existing institutional stores/contracts; this plane consumes bounded authority inputs and records execution-local state/receipts. The chat transcript is not a source of truth.

## Non-claims

- No native ChatGPT same-tab spawn is claimed.
- No Grok/Claude API connectivity is claimed without a real provider adapter.
- No provider access is fabricated by this layer.
- No new institutional authority is created by the execution ledger.
- No IB10 or Command B10 behavior is started.
