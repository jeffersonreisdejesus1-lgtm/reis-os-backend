# REIS-OS-HOST-ADAPTER-INVOCATION-CLOSURE-001

STATUS = IMPLEMENTATION_CANDIDATE / EXTERNAL_BINDING_HOLD

## Mission
Close the software gap between the existing REIS OS chat runtime and a material authorized execution host without simulating peer OCS execution.

## Implemented in this delta

- concrete `HttpHostAdapter`;
- strict receipt parsing;
- fail-closed transport and malformed-receipt behavior;
- authenticated internal dispatch endpoint at `/internal/chat-runtime/dispatch`;
- readiness endpoint at `/internal/chat-runtime/readiness`;
- environment-bound OCS binding registry;
- environment-bound host endpoint registry;
- explicit authority-edge allowlist;
- bearer-token protection for dispatch;
- tests for successful HTTP receipt parsing, transport failure and invalid receipt rejection.

## Required environment contract

`REIS_CHAT_BINDINGS_JSON`

Object keyed by OCS id. Each entry MUST contain:
`ocs_id`, `instance_id`, `generation`, `authority_ref`, `state_namespace`, `memory_namespace`, `host`.

`REIS_CHAT_HOSTS_JSON`

Object keyed by host name. Each entry MUST contain `endpoint` and may contain `token_env` and `timeout_seconds`.

`REIS_CHAT_AUTHORITY_EDGES_JSON`

Array of explicit edges in the form:
`PARENT->TARGET:PEER_OCS` or `PARENT->PARENT:AUXILIARY`.

`REIS_CHAT_RUNTIME_TOKEN`

Bearer token required by the dispatch surface.

Provider/host bearer tokens are referenced indirectly through each host entry's `token_env`. Secrets MUST NOT be embedded in binding JSON or source code.

## Runtime behavior

If bindings, hosts, authority edges or runtime token are missing, readiness returns HOLD.

Dispatch remains subject to the pre-existing runtime gates:
- parent instance/generation fencing;
- parent authority match;
- target identity resolution;
- auxiliary identity constraint;
- authority policy;
- target host binding;
- host adapter availability;
- host receipt binding validation;
- idempotency.

## Non-claims

This delta does NOT prove:
- a live provider endpoint exists;
- a provider endpoint can instantiate or recover a materially distinct OCS runtime actor;
- ChatGPT itself can call this internal endpoint as a custom connector from the current tab;
- end-to-end peer OCS invocation has occurred.

## Remaining gates

G1 = CI qualification of this exact head.
G2 = deploy isolated chat-runtime service with valid database/runtime configuration.
G3 = configure institutional bindings + authority edges + host endpoint(s).
G4 = prove remote host receipt from a materially distinct target instance.
G5 = expose an authorized connector/tool surface to the ChatGPT tab.
G6 = execute one non-production Nóesis -> peer OCS mission and reconcile receipt.
G7 = independent assurance.
G8 = Founder promotion gate.

## Current disposition

SOFTWARE_HOST_ADAPTER = MATERIALIZED
DISPATCH_API = MATERIALIZED
AUTHORITY_EDGE_GATE = MATERIALIZED
REMOTE_PROVIDER_BINDING = HOLD
LIVE_CHAT_RUNTIME_DEPLOYMENT = HOLD
CHATGPT_TAB_CONNECTOR = HOLD
REAL_PEER_OCS_INVOCATION = NOT_YET_PROVEN

No simulated OCS execution is authorized.
