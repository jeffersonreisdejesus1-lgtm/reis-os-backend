# REIS OS Chat Runtime — Multi-OCS E2E

## Objective

Materialize the application-level runtime required for a REIS OS chat surface to resolve and dispatch work to a peer OCS or an auxiliary instance without confusing host, model, tab, or connector identity with institutional OCS identity.

## Proven in this slice

- OCS resolution from bound institutional identity.
- Parent instance/generation fencing.
- Authority-policy check before dispatch.
- Peer OCS invocation contract.
- Auxiliary invocation constrained to the parent OCS identity.
- Host binding and host-adapter selection.
- Fail-closed behavior when a host adapter is unavailable.
- Host receipt binding validation.
- Idempotent replay and divergent-retry conflict.
- Correlation receipt returned to the command surface.

## Explicit boundary

This repository slice does **not** prove that the ChatGPT product surface can natively spawn another ChatGPT agent, Grok, Claude, or another provider model inside the same chat tab.

A real provider/host call requires an authorized `HostAdapter` implementation supplied by the execution environment. If no such adapter exists, dispatch must return HOLD; the runtime must never simulate execution.

## Identity rules

`CHAT != OCS`

`TAB != OCS`

`MODEL != OCS`

`HOST != OCS`

`AUXILIARY_AGENT_AUTHORITY ⊆ PARENT_OCS_MISSION_AUTHORITY`

`AUXILIARY_CREATION_DOES_NOT_CREATE_A_NEW_OCS`

`CAPABILITY != AUTHORITY`

`HANDOFF != AUTHORITY_TRANSFER`

## Target operational path

`REIS_OS_CHAT_SURFACE`
→ resolve parent binding
→ resolve target OCS
→ check generation / instance / authority
→ resolve bound host
→ invoke authorized host adapter
→ validate returned receipt against binding
→ persist/reconcile receipt in the calling command layer
→ continue mission

## Federated seats

The runtime can bind OCS instances to host names such as `GPT`, `GROK`, or `CLAUDE`, but host naming alone does not prove provider connectivity. Provider connectivity is proven only by a concrete host adapter plus a valid execution receipt.

## Non-claims

- No native same-tab provider spawn is claimed.
- No hidden multi-agent capability is claimed.
- No external provider execution is claimed by the in-process tests.
- No new OCS is created by an auxiliary invocation.
- No Command B10 behavior is started.
- No IB10 behavior is started.
