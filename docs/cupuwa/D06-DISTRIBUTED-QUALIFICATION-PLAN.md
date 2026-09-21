# D06 — Distributed Storage and Recovery Qualification

Status: NOT_EXECUTED / QUALIFICATION_PENDING

## Required environment

Two independent processes or hosts sharing one approved durable backend.
A local in-memory object or single-process SQLite connection is insufficient.

## Probes

- Q01: write in process A, read in process B;
- Q02: concurrent claim for one operation_id;
- Q03: conflicting payload across processes;
- Q04: owner expiration and stale-owner rejection;
- Q05: process A interruption during execution;
- Q06: process B recovery and reconciliation;
- Q07: replay after recovery without duplicate effect;
- Q08: corrupt or missing receipt fails closed;
- Q09: deterministic recovery receipt;
- Q10: authority reference preserved without expansion.

## Required evidence

Each probe must record:

- exact repository and HEAD;
- backend and version;
- process/host identities;
- operation_id and payload fingerprint;
- timestamps;
- state transitions;
- receipts and hashes;
- observed readback;
- command and result;
- artifact hash.

## Acceptance

PASS requires all probes to pass with no duplicate canonical effect,
no blind retry, no false success, and no authority expansion.

Any unavailable host/backend, missing readback, or unexecuted probe keeps
the procedure in HOLD.

## Current result

No distributed backend is bound in this repository branch.
No multi-process or multi-host execution has been performed.
